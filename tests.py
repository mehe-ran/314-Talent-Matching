import unittest
from werkzeug.security import generate_password_hash
import io
import os
import shutil

from app import app, db
from models import Candidate, Employer, WorkExperience, JobPosting, Skill
from utils.matcher import find_close_matches


class TalentMatchingTestCase(unittest.TestCase):
    def setUp(self):
        # set up a test client
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SECRET_KEY'] = 'test-secret'
        app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'test_uploads') # Use absolute path for consistency
        self.client = app.test_client()

        # create upload folder
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        # create all tables
        with app.app_context():
            db.create_all()
            # add a test user
            hashed_password = generate_password_hash('testpassword')
            test_candidate = Candidate(full_name='Test User', email='test@example.com', password_hash=hashed_password)
            db.session.add(test_candidate)

            # Add all skills used in tests
            skill_python = Skill(skill_name='Python')
            skill_flask = Skill(skill_name='Flask')
            skill_sql = Skill(skill_name='SQL')
            skill_react = Skill(skill_name='React')
            skill_go = Skill(skill_name='Go')
            skill_javascript = Skill(skill_name='JavaScript')
            skill_java = Skill(skill_name='Java')
            skill_csharp = Skill(skill_name='C#')
            skill_cpp = Skill(skill_name='C++')
            skill_ruby = Skill(skill_name='Ruby')
            skill_php = Skill(skill_name='PHP')
            skill_swift = Skill(skill_name='Swift')
            skill_kotlin = Skill(skill_name='Kotlin')
            skill_typescript = Skill(skill_name='TypeScript')
            skill_r = Skill(skill_name='R')
            skill_scala = Skill(skill_name='Scala')
            skill_rust = Skill(skill_name='Rust')
            db.session.add_all([
                skill_python, skill_flask, skill_sql, skill_react, skill_go, skill_javascript,
                skill_java, skill_csharp, skill_cpp, skill_ruby, skill_php, skill_swift,
                skill_kotlin, skill_typescript, skill_r, skill_scala, skill_rust
            ])

            db.session.commit()

    def tearDown(self):
        # drop all tables
        with app.app_context():
            db.session.remove()
            db.drop_all()
        
        # remove upload folder
        shutil.rmtree(app.config['UPLOAD_FOLDER'])

    def test_candidate_can_have_work_experience(self):
        with app.app_context():
            candidate = Candidate.query.filter_by(email='test@example.com').first()
            experience = WorkExperience(
                job_title='Software Engineer',
                company_name='Tech Corp',
                description='Developed cool things.'
            )
            candidate.work_experiences.append(experience)
            db.session.commit()

            self.assertEqual(len(candidate.work_experiences), 1)
            self.assertEqual(candidate.work_experiences[0].company_name, 'Tech Corp')

    def test_fuzzy_matching_function(self):
        # test the core fuzzy matching utility
        possibilities = ['python developer', 'java developer', 'react engineer']
        keyword = 'pyhton dev'
        matches = find_close_matches(keyword, possibilities, n=1, cutoff=0.6)
        self.assertEqual(matches, ['python developer'])

    def test_successful_candidate_login(self):
        # test login with correct credentials for a candidate
        with self.client:
            response = self.client.post('/login', data={
                'email': 'test@example.com',
                'password': 'testpassword'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            # Check for a welcome message on the dashboard
            self.assertIn(b'Login successful.', response.data)
            with self.client.session_transaction() as sess:
                self.assertEqual(sess.get('user_type'), 'candidate')
                self.assertIsNotNone(sess.get('user_id'))

    def test_failed_login_wrong_password(self):
        # test login with incorrect password
        response = self.client.post('/login', data={
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Incorrect password, please try again.', response.data)

    def test_failed_login_no_account(self):
        # test login with an email that does not exist
        response = self.client.post('/login', data={
            'email': 'nouser@example.com',
            'password': 'somepassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'No account found for that email address.', response.data)

    def test_failed_login_missing_fields(self):
        # test login with missing email
        response = self.client.post('/login', data={
            'email': '',
            'password': 'somepassword'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Please enter both email and password.', response.data)

    def test_employer_can_be_member(self):
        with app.app_context():
            hashed_password = generate_password_hash('testpassword')
            employer = Employer(
                company_name='Member Corp',
                contact_email='member@corp.com',
                password_hash=hashed_password,
                is_member=True
            )
            db.session.add(employer)
            db.session.commit()
            self.assertTrue(employer.is_member)

    def test_registration_hashes_password(self):
        # test that a new user is created with a hashed password
        with self.client.application.app_context():
            response = self.client.post('/register', data={
                'full_name': 'New User',
                'email': 'newuser@example.com',
                'password': 'a-secure-password',
                'user_type': 'candidate'
            }, follow_redirects=True)
            self.assertEqual(response.status_code, 200)

            # Check that the user was created
            new_candidate = Candidate.query.filter_by(email='newuser@example.com').first()
            self.assertIsNotNone(new_candidate)
            self.assertTrue(hasattr(new_candidate, 'password_hash'))
            self.assertNotEqual(new_candidate.password_hash, 'a-secure-password')

    def test_recommendation_returns_skilled_matches(self):
        with app.app_context():
            # 1. Setup: Create skills, a candidate with skills, and jobs with skills
            skill1 = Skill.query.filter_by(skill_name='Python').first()
            skill2 = Skill.query.filter_by(skill_name='Flask').first()
            skill3 = Skill.query.filter_by(skill_name='SQL').first()

            candidate = Candidate.query.filter_by(email='test@example.com').first()
            candidate.skills.extend([skill1, skill2]) # Candidate knows Python and Flask

            employer = Employer(company_name='TestCorp', contact_email='hr@testcorp.com', password_hash=generate_password_hash('password'))
            db.session.add(employer)
            db.session.commit()

            # Job 1: Perfect match (2 skills)
            job1 = JobPosting(job_title='Python/Flask Dev', job_description='...', employer_id=employer.employer_id, skills=[skill1, skill2])
            # Job 2: Partial match (1 skill)
            job2 = JobPosting(job_title='Python Scripter', job_description='...', employer_id=employer.employer_id, skills=[skill1])
            # Job 3: No match
            job3 = JobPosting(job_title='Database Admin', job_description='...', employer_id=employer.employer_id, skills=[skill3])
            # Job 4: Another partial match (1 skill)
            job4 = JobPosting(job_title='Flask API Dev', job_description='...', employer_id=employer.employer_id, skills=[skill2])
            
            db.session.add_all([job1, job2, job3, job4])
            db.session.commit()

            # Store titles before context closes
            job1_title = job1.job_title
            job2_title = job2.job_title
            job3_title = job3.job_title
            job4_title = job4.job_title

        # 2. Action: Login as candidate and hit the recommend route
        with self.client:
            self.client.post('/login', data={'email': 'test@example.com', 'password': 'testpassword'})
            response = self.client.get('/recommend')
        
        self.assertEqual(response.status_code, 200)
        
        # 3. Assert: Check that the correct jobs are recommended in the correct order
        response_data = response.get_data(as_text=True)
        self.assertIn(job1_title, response_data)
        self.assertIn(job2_title, response_data)
        self.assertIn(job4_title, response_data)
        self.assertNotIn(job3_title, response_data)
        
        # Check scores
        self.assertIn('Match Score: 100%', response_data)
        self.assertIn('Match Score: 50%', response_data)
        
        # Check order - job1 must appear before both job2 and job4
        job1_pos = response_data.find(job1_title)
        job2_pos = response_data.find(job2_title)
        job4_pos = response_data.find(job4_title)

        self.assertTrue(job1_pos < job2_pos and job1_pos < job4_pos)

    def test_recommendation_limit_for_non_members(self):
        with app.app_context():
            # Setup: 1 candidate, 1 skill, 12 jobs requiring that skill
            skill = Skill.query.filter_by(skill_name='Go').first()

            candidate = Candidate.query.filter_by(email='test@example.com').first()
            candidate.skills.append(skill)
            candidate.is_member = False # Ensure user is not a member

            employer = Employer(company_name='GoCorp', contact_email='hr@gocorp.com', password_hash=generate_password_hash('password'))
            db.session.add(employer)
            db.session.commit()

            for i in range(12):
                job = JobPosting(job_title=f'Go Developer #{i+1}', job_description='...', employer_id=employer.employer_id, skills=[skill])
                db.session.add(job)
            db.session.commit()
        
        # Action: Login and get recommendations
        with self.client:
            self.client.post('/login', data={'email': 'test@example.com', 'password': 'testpassword'})
            response = self.client.get('/recommend')

        self.assertEqual(response.status_code, 200)
        response_data = response.get_data(as_text=True)

        # Assert: Check that only 10 jobs are present
        self.assertIn('Go Developer #10', response_data)
        self.assertNotIn('Go Developer #11', response_data)
        self.assertEqual(response_data.count('<h5 class="fw-bold mb-0 me-3">'), 10)

    def test_search_filter_by_work_mode(self):
        with app.app_context():
            employer = Employer(company_name='FilterCorp', contact_email='hr@filtercorp.com', password_hash=generate_password_hash('password'))
            db.session.add(employer)
            db.session.commit()

            job1 = JobPosting(job_title='Remote Job', job_description='...', employer_id=employer.employer_id, work_mode='Remote')
            job2 = JobPosting(job_title='On-site Job', job_description='...', employer_id=employer.employer_id, work_mode='On-site')
            db.session.add_all([job1, job2])
            db.session.commit()
        
        response = self.client.get('/search?work_mode=Remote')
        self.assertEqual(response.status_code, 200)
        response_data = response.get_data(as_text=True)

        self.assertIn('Remote Job', response_data)
        self.assertNotIn('On-site Job', response_data)

    def test_search_for_candidates(self):
        with app.app_context():
            # Setup skills
            skill_py = Skill.query.filter_by(skill_name='Python').first()
            skill_js = Skill.query.filter_by(skill_name='JavaScript').first()

            # Setup candidates
            c1 = Candidate(full_name='Python Dev Remote', email='c1@test.com', password_hash='...', location='Remote', skills=[skill_py])
            c2 = Candidate(full_name='JS Dev Remote', email='c2@test.com', password_hash='...', location='Remote', skills=[skill_js])
            c3 = Candidate(full_name='Python Dev Office', email='c3@test.com', password_hash='...', location='Office', skills=[skill_py])
            db.session.add_all([c1, c2, c3])

            # Setup employer to log in
            employer = Employer(company_name='SearcherCorp', contact_email='searcher@corp.com', password_hash=generate_password_hash('password'))
            db.session.add(employer)
            db.session.commit()
        
        # Action: Login as employer and search
        with self.client:
            self.client.post('/login', data={'email': 'searcher@corp.com', 'password': 'password'})
            response = self.client.get('/search/candidates?skills=Python&location=Remote')

        self.assertEqual(response.status_code, 200)
        response_data = response.get_data(as_text=True)

        # Assert: only the correct candidate is found
        self.assertIn('Python Dev Remote', response_data)
        self.assertNotIn('JS Dev Remote', response_data)
        self.assertNotIn('Python Dev Office', response_data)

    def test_get_edit_profile_page(self):
        with self.client:
            # Login as the test candidate
            self.client.post('/login', data={'email': 'test@example.com', 'password': 'testpassword'})
            
            response = self.client.get('/profile/edit')
            self.assertEqual(response.status_code, 200)
            
            response_data = response.get_data(as_text=True)
            self.assertIn('value="Test User"', response_data)
            self.assertIn('value="test@example.com"', response_data)

    def test_post_edit_profile_page(self):
        with self.client:
            self.client.post('/login', data={'email': 'test@example.com', 'password': 'testpassword'})
            
            # Simulate file upload
            data = {
                'full_name': 'Updated Name',
                'location': 'New Location',
                'preferred_work_mode': 'Hybrid',
                'years_of_experience': 5, # Added years_of_experience
                'resume': (io.BytesIO(b"this is a test resume"), 'test.pdf')
            }
            response = self.client.post('/profile/edit', data=data, 
                                        follow_redirects=True, content_type='multipart/form-data')
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Profile updated successfully!', response.data)

        with app.app_context():
            updated_candidate = db.session.get(Candidate, 1)
            self.assertEqual(updated_candidate.full_name, 'Updated Name')
            self.assertEqual(updated_candidate.location, 'New Location')
            self.assertEqual(updated_candidate.preferred_work_mode, 'Hybrid')
            self.assertEqual(updated_candidate.years_of_experience, 5) # Assert years_of_experience
            self.assertIsNotNone(updated_candidate.resume_filename)
            self.assertTrue('test.pdf' in updated_candidate.resume_filename)

    def test_get_create_job_page(self):
        with self.client:
            # Setup and login as an employer
            with app.app_context():
                employer = Employer(company_name='JobPoster', contact_email='poster@corp.com', password_hash=generate_password_hash('password'))
                db.session.add(employer)
                db.session.commit()
            
            self.client.post('/login', data={'email': 'poster@corp.com', 'password': 'password'})

            response = self.client.get('/jobs/new')
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Create a New Job Posting', response.data)

    def test_post_create_job_page(self):
        with self.client:
            # Setup and login as an employer
            with app.app_context():
                employer = Employer(company_name='JobPoster', contact_email='poster@corp.com', password_hash=generate_password_hash('password'))
                db.session.add(employer)
                db.session.commit()
                employer_id = employer.employer_id

            self.client.post('/login', data={'email': 'poster@corp.com', 'password': 'password'})

            response = self.client.post('/jobs/new', data={
                'job_title': 'New Job Title',
                'job_description': 'A great new job.',
                'location': 'Office',
                'work_mode': 'On-site',
                'required_education_level': "Bachelor's",
                'required_years_of_experience': 2,
                'salary_min': 80000,
                'salary_max': 100000,
                'job_type': 'Full-time'
            }, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Job posted successfully!', response.data)

        with app.app_context():
            new_job = JobPosting.query.filter_by(job_title='New Job Title').first()
            self.assertIsNotNone(new_job)
            self.assertEqual(new_job.employer_id, employer_id)
            self.assertEqual(new_job.location, 'Office')
            self.assertEqual(new_job.required_education_level, "Bachelor's")
            self.assertEqual(new_job.required_years_of_experience, 2)
            self.assertEqual(new_job.salary_min, 80000)
            self.assertEqual(new_job.salary_max, 100000)
            self.assertEqual(new_job.job_type, 'Full-time')

    def test_search_with_new_filters(self):
        with app.app_context():
            employer = Employer(company_name='FilterCorp', contact_email='hr@filtercorp.com', password_hash=generate_password_hash('password'))
            db.session.add(employer)
            db.session.commit()

            # Create a set of jobs to filter
            job1 = JobPosting(job_title='Senior Full-time', job_description='Desc 1', employer_id=employer.employer_id, job_type='Full-time', required_years_of_experience=5, salary_min=100000, salary_max=120000)
            job2 = JobPosting(job_title='Junior Full-time', job_description='Desc 2', employer_id=employer.employer_id, job_type='Full-time', required_years_of_experience=1, salary_min=60000, salary_max=80000)
            job3 = JobPosting(job_title='Senior Part-time', job_description='Desc 3', employer_id=employer.employer_id, job_type='Part-time', required_years_of_experience=5, salary_min=50000, salary_max=60000)
            db.session.add_all([job1, job2, job3])
            db.session.commit()

        # Search for a junior, full-time role
        response = self.client.get('/search?job_type=Full-time&experience=2&salary=70000')
        self.assertEqual(response.status_code, 200)
        response_data = response.get_data(as_text=True)

        self.assertIn('Junior Full-time', response_data)
        self.assertNotIn('Senior Full-time', response_data)
        self.assertNotIn('Senior Part-time', response_data)
    
    def test_employer_recommendations(self):
        with app.app_context():
            # Skills
            skill_py = Skill.query.filter_by(skill_name='Python').first()
            skill_flask = Skill.query.filter_by(skill_name='Flask').first()

            # Employer (non-member)
            employer = Employer(company_name='RecommenderCorp', contact_email='rec@corp.com', password_hash=generate_password_hash('password'), is_member=False)
            db.session.add(employer)
            db.session.commit()

            # Job Posting requiring Python and Flask
            job = JobPosting(job_title='Python/Flask Guru', job_description='Desc', employer_id=employer.employer_id, skills=[skill_py, skill_flask])
            db.session.add(job)
            db.session.commit()
            job_id = job.job_id

            # Candidates
            c1 = Candidate(full_name='Perfect Match', email='c1@test.com', password_hash='...', skills=[skill_py, skill_flask])
            c2 = Candidate(full_name='Partial Match', email='c2@test.com', password_hash='...', skills=[skill_py])
            c3 = Candidate(full_name='No Match', email='c3@test.com', password_hash='...', skills=[])
            db.session.add_all([c1, c2, c3])
            
            # Create 10 more partial matches to test the non-member limit
            for i in range(10):
                c = Candidate(full_name=f'Filler {i}', email=f'f{i}@test.com', password_hash='...', skills=[skill_py])
                db.session.add(c)
            db.session.commit()

        # Action
        with self.client:
            self.client.post('/login', data={'email': 'rec@corp.com', 'password': 'password'})
            response = self.client.get(f'/jobs/{job_id}/recommendations')
        
        self.assertEqual(response.status_code, 200)
        response_data = response.get_data(as_text=True)

        # Assertions
        self.assertIn('Perfect Match', response_data)
        self.assertIn('Partial Match', response_data)
        self.assertNotIn('No Match', response_data)
        
        # Check scores
        self.assertIn('100% Match', response_data)
        self.assertIn('50% Match', response_data)

        # Check order
        self.assertTrue(response_data.find('Perfect Match') < response_data.find('Partial Match'))

        # Check non-member limit (1 perfect + 9 partial = 10 total)
        self.assertEqual(response_data.count('<h5 class="fw-bold mb-0 me-3">'), 10)


    def test_candidate_can_update_skills(self):
        with app.app_context():
            # Add some skills to the test candidate initially
            candidate = db.session.get(Candidate, 1)
            python_skill = Skill.query.filter_by(skill_name='Python').first()
            sql_skill = Skill.query.filter_by(skill_name='SQL').first()
            candidate.skills.append(python_skill)
            candidate.skills.append(sql_skill)
            db.session.commit()

            # Get skill IDs for form submission
            flask_skill = Skill.query.filter_by(skill_name='Flask').first()
            react_skill = Skill.query.filter_by(skill_name='React').first()
            
            # Action: Login and update profile with new skills
        with self.client:
            self.client.post('/login', data={'email': 'test@example.com', 'password': 'testpassword'})
            
            data = {
                'full_name': 'Test User', # Keep existing name
                'email': 'test@example.com', # Keep existing email
                'skills': [str(flask_skill.skill_id), str(react_skill.skill_id)] # Update skills
            }
            response = self.client.post('/profile/edit', data=data, follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Profile updated successfully!', response.data)

        with app.app_context():
            updated_candidate = db.session.get(Candidate, 1)
            updated_skill_names = {skill.skill_name for skill in updated_candidate.skills}
            
            self.assertIn('Flask', updated_skill_names)
            self.assertIn('React', updated_skill_names)
            self.assertNotIn('Python', updated_skill_names)
            self.assertNotIn('SQL', updated_skill_names)
            self.assertEqual(len(updated_skill_names), 2)

