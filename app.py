from flask import Flask, flash, redirect, render_template, request, url_for
from sqlalchemy import or_

from models import Candidate, Employer, JobPosting, db


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///talent_matching.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'dev-secret-key'

db.init_app(app)


with app.app_context():
	db.create_all()


@app.route('/')
def hello_world():
	return 'Hello, World!'


@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		email = request.form.get('email', '').strip().lower()
		password = request.form.get('password', '').strip()

		if not email or not password:
			flash('Please enter both email and password.', 'danger')
			return redirect(url_for('login'))

		candidate = Candidate.query.filter_by(email=email).first()
		employer = Employer.query.filter_by(contact_email=email).first()

		if candidate or employer:
			flash('Login successful.', 'success')
			return redirect(url_for('hello_world'))

		flash('No account found for that email address.', 'danger')
		return redirect(url_for('login'))

	return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
	if request.method == 'POST':
		name = request.form.get('name', '').strip()
		email = request.form.get('email', '').strip().lower()
		password = request.form.get('password', '').strip()
		role = request.form.get('role', '').strip().lower()

		if not name or not email or not password or role not in {'candidate', 'employer'}:
			flash('Please complete all fields before creating an account.', 'danger')
			return redirect(url_for('register'))

		if Candidate.query.filter_by(email=email).first() or Employer.query.filter_by(contact_email=email).first():
			flash('An account already exists for that email address.', 'warning')
			return redirect(url_for('register'))

		if role == 'candidate':
			account = Candidate(full_name=name, email=email)
		else:
			account = Employer(company_name=name, contact_email=email)

		db.session.add(account)
		db.session.commit()

		flash('Account created successfully.', 'success')
		return redirect(url_for('login'))

	return render_template('register.html')


@app.route('/candidate')
def candidate_dashboard():
	return render_template('candidate_dashboard.html')


@app.route('/employer')
def employer_dashboard():
	return render_template('employer_dashboard.html')


@app.route('/search')
def search():
	keywords = request.args.get('keywords', '').strip()
	location = request.args.get('location', '').strip()

	query = JobPosting.query

	# if keywords are provided, search in title and description
	if keywords:
		keyword_filter = or_(
			JobPosting.job_title.ilike(f'%{keywords}%'),
			JobPosting.job_description.ilike(f'%{keywords}%')
		)
		query = query.filter(keyword_filter)

	# if location is provided, filter by location
	if location:
		query = query.filter(JobPosting.location.ilike(f'%{location}%'))

	jobs = query.all()
	return render_template('search_results.html', jobs=jobs, search_keywords=keywords, search_location=location)


if __name__ == '__main__':
	app.run(debug=True)
