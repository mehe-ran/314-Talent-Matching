from app import app, db
from models import Candidate, Employer, JobPosting, Skill
from werkzeug.security import generate_password_hash

def seed_data():
    with app.app_context():
        # Clear existing data
        # db.reflect()
        # db.drop_all()
        db.create_all()

        # === Create Skills ===
        skills_list = [
            'Python', 'Flask', 'SQL', 'React', 'Go', 'JavaScript', 'Java', 'C#', 
            'C++', 'Ruby', 'PHP', 'Swift', 'Kotlin', 'TypeScript', 'R', 'Scala', 'Rust'
        ]
        skill_objects = {name: Skill(skill_name=name) for name in skills_list}
        db.session.add_all(skill_objects.values())
        db.session.commit()
        print("Skills seeded.")

        # === Create Employers ===
        employers = []
        for i in range(1, 6):
            employer = Employer(
                company_name=f'TechCorp{i}',
                contact_email=f'hr@techcorp{i}.com',
                password_hash=generate_password_hash(f'password{i}')
            )
            employers.append(employer)
        db.session.add_all(employers)
        db.session.commit()
        print(f"{len(employers)} employers seeded.")

        # === Create Candidates ===
        candidates = []
        candidate_skills = {
            1: ['Python', 'Flask', 'SQL'],
            2: ['JavaScript', 'React', 'TypeScript'],
            3: ['Java', 'Spring', 'SQL'],
            4: ['Go', 'SQL', 'Rust'],
            5: ['C#', '.NET', 'SQL']
        }
        for i in range(1, 6):
            candidate = Candidate(
                full_name=f'Candidate {i}',
                email=f'candidate{i}@test.com',
                password_hash=generate_password_hash(f'password{i}'),
                years_of_experience=i * 2,
                location='Singapore'
            )
            # Add skills to candidate
            if i in candidate_skills:
                for skill_name in candidate_skills[i]:
                    # Create skill if it doesn't exist
                    skill_obj = skill_objects.get(skill_name)
                    if not skill_obj:
                        skill_obj = Skill(skill_name=skill_name)
                        skill_objects[skill_name] = skill_obj
                        db.session.add(skill_obj)
                    candidate.skills.append(skill_obj)
            
            candidates.append(candidate)
        db.session.add_all(candidates)
        db.session.commit()
        print(f"{len(candidates)} candidates seeded.")

        # === Create Job Postings ===
        jobs = []
        job_skills = {
            1: ['Python', 'Flask', 'SQL'], # Tailored for Candidate 1
            2: ['JavaScript', 'React', 'TypeScript'], # Tailored for Candidate 2
            3: ['Java', 'Spring', 'SQL'], # Tailored for Candidate 3
            4: ['Ruby', 'PHP'],
            5: ['Swift', 'Kotlin']
        }
        for i in range(1, 6):
            job = JobPosting(
                employer=employers[i-1],
                job_title=f'Job Title {i}',
                job_description=f'Description for job {i}',
                location='Singapore',
                work_mode='Hybrid',
                required_years_of_experience=i * 2,
            )
            # Add skills to job
            if i in job_skills:
                for skill_name in job_skills[i]:
                    skill_obj = skill_objects.get(skill_name)
                    if skill_obj:
                        job.skills.append(skill_obj)
            
            jobs.append(job)
        db.session.add_all(jobs)
        db.session.commit()
        print(f"{len(jobs)} job postings seeded.")
        
        print("Database seeded successfully!")
        print("Sample Credentials:")
        print("--------------------")
        for i in range(1, 6):
            print(f"Candidate {i}: candidate{i}@test.com / password{i}")
        for i in range(1, 6):
            print(f"Employer {i}: hr@techcorp{i}.com / password{i}")


if __name__ == '__main__':
    seed_data()
