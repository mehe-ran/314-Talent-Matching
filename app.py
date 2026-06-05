import os
import json
from functools import wraps
from flask import Flask, flash, redirect, render_template, request, url_for, session, send_from_directory
from sqlalchemy import or_, func
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from models import Candidate, Employer, JobPosting, Skill, db
from utils.matcher import find_close_matches, calculate_job_recommendations, calculate_candidate_recommendations, \
    get_synonyms

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///talent_matching.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'docx'}

db.init_app(app)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You must be logged in to view this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/dashboard')
@login_required
def dashboard():
    if session.get('user_type') == 'candidate':
        return redirect(url_for('candidate_dashboard'))
    elif session.get('user_type') == 'employer':
        return redirect(url_for('employer_dashboard'))
    else:
        flash('Invalid user type in session.', 'danger')
        return redirect(url_for('login'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/upgrade')
@login_required
def upgrade():
    return render_template('upgrade.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return redirect(url_for('login'))

        user = Candidate.query.filter_by(email=email).first()
        user_type = 'candidate'
        if not user:
            user = Employer.query.filter_by(contact_email=email).first()
            user_type = 'employer'

        if user and check_password_hash(user.password_hash, password):
            session.clear()
            if user_type == 'candidate':
                session['user_id'] = user.candidate_id
            else:
                session['user_id'] = user.employer_id
            session['user_type'] = user_type
            flash('Login successful.', 'success')
            return redirect(url_for('dashboard'))
        elif user:
            flash('Incorrect password, please try again.', 'danger')
        else:
            flash('No account found for that email address.', 'danger')

        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        user_type = request.form.get('user_type', '').strip().lower()

        if not full_name or not email or not password or user_type not in {'candidate', 'employer'}:
            flash('Please complete all fields before creating an account.', 'danger')
            return redirect(url_for('register'))

        if Candidate.query.filter_by(email=email).first() or Employer.query.filter_by(contact_email=email).first():
            flash('An account already exists for that email address.', 'warning')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)

        if user_type == 'candidate':
            account = Candidate(full_name=full_name, email=email, password_hash=hashed_password)
        else:
            # For employer, the form sends 'full_name', but the model expects 'company_name'
            account = Employer(company_name=full_name, contact_email=email, password_hash=hashed_password)

        db.session.add(account)
        db.session.commit()

        flash('Account created successfully. You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/candidate_dashboard')
@login_required
def candidate_dashboard():
    candidate = db.session.get(Candidate, session['user_id'])
    return render_template('candidate_dashboard.html', title='Candidate Dashboard', candidate=candidate)


@app.route('/employer_dashboard')
@login_required
def employer_dashboard():
    employer = db.session.get(Employer, session['user_id'])
    return render_template('employer_dashboard.html', title='Employer Dashboard', employer=employer)


@app.route('/search')
def search():
    keywords = request.args.get('keywords', '').strip()
    location = request.args.get('location', '').strip()
    work_mode = request.args.get('work_mode', '').strip()
    job_type = request.args.get('job_type', '').strip()
    experience = request.args.get('experience', type=int)
    salary = request.args.get('salary', type=int)

    query = JobPosting.query

    # if keywords are provided, search in title and description
    if keywords:
        search_terms = get_synonyms(keywords)

        # get all unique job titles to use for fuzzy matching
        all_job_titles = [job[0] for job in db.session.query(JobPosting.job_title).distinct().all()]
        close_title_matches = find_close_matches(keywords, all_job_titles)
        search_terms.update(close_title_matches)

        keyword_filters = []
        for term in search_terms:
            keyword_filters.append(JobPosting.job_title.ilike(f'%{term}%'))
            keyword_filters.append(JobPosting.job_description.ilike(f'%{term}%'))

        query = query.filter(or_(*keyword_filters))

    # if location is provided, filter by location
    if location:
        query = query.filter(JobPosting.location.ilike(f'%{location}%'))

    # if work_mode is provided, filter by it
    if work_mode:
        query = query.filter(JobPosting.work_mode == work_mode)

    # Add new filters
    if job_type:
        query = query.filter(JobPosting.job_type == job_type)

    if experience is not None:
        query = query.filter(JobPosting.required_years_of_experience <= experience)

    if salary is not None:
        query = query.filter(JobPosting.salary_min <= salary, JobPosting.salary_max >= salary)

    jobs = query.all()
    return render_template('search_results.html', jobs=jobs, search_keywords=keywords, search_location=location,
                           search_work_mode=work_mode)


@app.route('/recommend')
@login_required
def recommend():
    if session['user_type'] != 'candidate':
        flash('Recommendations are only available for candidates.', 'warning')
        return redirect(url_for('dashboard'))

    candidate = db.session.get(Candidate, session['user_id'])
    if not candidate:
        flash('Could not find your candidate profile.', 'danger')
        session.clear()
        return redirect(url_for('login'))

    all_jobs = JobPosting.query.all()

    recommended_jobs = calculate_job_recommendations(candidate, all_jobs)

    # Limit recommendations for non-members
    if not candidate.is_member:
        recommended_jobs = recommended_jobs[:10]

    return render_template('recommendations.html', jobs=recommended_jobs, candidate=candidate)


@app.route('/search/candidates')
@login_required
def search_candidates():
    if session.get('user_type') != 'employer':
        flash('Only employers can search for candidates.', 'warning')
        return redirect(url_for('dashboard'))

    skills_str = request.args.get('skills', '').strip()
    location = request.args.get('location', '').strip()

    query = Candidate.query

    if skills_str:
        skill_names = [s.strip() for s in skills_str.split(',')]
        query = query.join(Candidate.skills).filter(Skill.skill_name.in_(skill_names))

    if location:
        query = query.filter(Candidate.location.ilike(f'%{location}%'))

    candidates = query.all()

    return render_template('candidate_search_results.html', candidates=candidates)


@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if session['user_type'] != 'candidate':
        flash('This page is only available for candidates.', 'warning')
        return redirect(url_for('dashboard'))

    candidate = db.session.get(Candidate, session['user_id'])
    if candidate is None:
        flash('Candidate profile not found.', 'danger')
        session.clear()
        return redirect(url_for('login'))

    if request.method == 'POST':
        candidate.full_name = request.form.get('full_name', candidate.full_name)
        candidate.location = request.form.get('location', candidate.location)
        candidate.preferred_work_mode = request.form.get('preferred_work_mode', candidate.preferred_work_mode)

        years_of_experience_str = request.form.get('years_of_experience')
        if years_of_experience_str:
            try:
                candidate.years_of_experience = int(years_of_experience_str)
            except ValueError:
                flash('Years of Experience must be a valid number.', 'danger')
                return redirect(url_for('edit_profile'))
        else:
            candidate.years_of_experience = None  # Clear if empty

        # Universal Skills Parsing Logic
        skills_raw = request.form.getlist('skills')
        skill_names = []
        if skills_raw:
            if len(skills_raw) == 1 and skills_raw[0].strip().startswith('['):
                try:
                    skills_data = json.loads(skills_raw[0])
                    if isinstance(skills_data, list):
                        skill_names = [item['value'].strip() for item in skills_data if
                                       isinstance(item, dict) and item.get('value')]
                except json.JSONDecodeError:
                    skill_names = [s.strip() for s in skills_raw[0].split(',') if s.strip()]
            elif len(skills_raw) == 1 and ',' in skills_raw[0]:
                skill_names = [s.strip() for s in skills_raw[0].split(',') if s.strip()]
            else:
                skill_names = [s.strip() for s in skills_raw if s.strip()]

        candidate.skills.clear()
        for skill_name in skill_names:
            skill = Skill.query.filter(func.lower(Skill.skill_name) == skill_name.lower()).first()
            if not skill:
                skill = Skill(skill_name=skill_name)
                db.session.add(skill)
            candidate.skills.append(skill)

        if 'resume' in request.files:
            file = request.files['resume']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{candidate.candidate_id}_{filename}"
                try:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    candidate.resume_filename = unique_filename
                    flash('Resume uploaded successfully!', 'success')
                except Exception as e:
                    app.logger.error(f"Error uploading resume for candidate {candidate.candidate_id}: {e}")
                    flash('An error occurred during resume upload. Please try again.', 'danger')
            elif file and not file.filename:
                flash('No selected file for resume upload.', 'warning')
            elif file and not allowed_file(file.filename):
                flash('Invalid file type for resume. Accepted formats: PDF, DOCX.', 'warning')

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    all_skills = Skill.query.all()
    return render_template('edit_profile.html', candidate=candidate, all_skills=all_skills)


@app.route('/jobs/new', methods=['GET', 'POST'])
@login_required
def create_job():
    if session.get('user_type') != 'employer':
        flash('Only employers can post new jobs.', 'warning')
        return redirect(url_for('dashboard'))

    all_skills = Skill.query.all()

    if request.method == 'POST':
        new_job = JobPosting(
            job_title=request.form['job_title'],
            job_description=request.form['job_description'],
            location=request.form['location'],
            work_mode=request.form['work_mode'],
            employer_id=session['user_id'],
            required_education_level=request.form.get('required_education_level'),
            required_years_of_experience=request.form.get('required_years_of_experience', type=int),
            salary_min=request.form.get('salary_min', type=int),
            salary_max=request.form.get('salary_max', type=int),
            job_type=request.form.get('job_type')
        )

        # Universal Skills Parsing Logic
        skills_raw = request.form.getlist('skills')
        skill_names = []
        if skills_raw:
            if len(skills_raw) == 1 and skills_raw[0].strip().startswith('['):
                try:
                    skills_data = json.loads(skills_raw[0])
                    if isinstance(skills_data, list):
                        skill_names = [item['value'].strip() for item in skills_data if
                                       isinstance(item, dict) and item.get('value')]
                except json.JSONDecodeError:
                    skill_names = [s.strip() for s in skills_raw[0].split(',') if s.strip()]
            elif len(skills_raw) == 1 and ',' in skills_raw[0]:
                skill_names = [s.strip() for s in skills_raw[0].split(',') if s.strip()]
            else:
                skill_names = [s.strip() for s in skills_raw if s.strip()]

        for skill_name in skill_names:
            skill = Skill.query.filter(func.lower(Skill.skill_name) == skill_name.lower()).first()
            if not skill:
                skill = Skill(skill_name=skill_name)
                db.session.add(skill)
            new_job.skills.append(skill)

        db.session.add(new_job)
        db.session.commit()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('employer_dashboard'))

    return render_template('create_job.html', all_skills=all_skills)


@app.route('/jobs/<int:job_id>/recommendations')
@login_required
def job_recommendations(job_id):
    if session.get('user_type') != 'employer':
        flash('Only employers can view candidate recommendations.', 'warning')
        return redirect(url_for('dashboard'))

    job = db.session.get(JobPosting, job_id)
    if not job or job.employer_id != session['user_id']:
        flash('Job not found or you do not have permission to view it.', 'danger')
        return redirect(url_for('employer_dashboard'))

    all_candidates = Candidate.query.all()
    employer = db.session.get(Employer, session['user_id'])

    recommended_candidates = calculate_candidate_recommendations(job, all_candidates)

    if not employer.is_member:
        recommended_candidates = recommended_candidates[:10]

    return render_template('employer_recommendations.html', candidates=recommended_candidates, job=job,
                           employer=employer)


@app.route('/uploads/<filename>')
@login_required
def download_resume(filename):
    candidate = db.session.get(Candidate, session['user_id'])
    if candidate and candidate.resume_filename == filename:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    flash('You do not have permission to access this file.', 'danger')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)