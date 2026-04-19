from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Candidate(db.Model):
    __tablename__ = 'candidate'

    candidate_id = db.Column('CandidateID', db.Integer, primary_key=True)
    full_name = db.Column('FullName', db.String(120), nullable=False)
    email = db.Column('Email', db.String(120), unique=True, nullable=False)
    education_level = db.Column('EducationLevel', db.String(120), nullable=True)
    major = db.Column('Major', db.String(120), nullable=True)
    years_of_experience = db.Column('YearsOfExperience', db.Integer, nullable=True)
    preferred_work_mode = db.Column('PreferredWorkMode', db.String(50), nullable=True)
    is_member = db.Column('IsMember', db.Boolean, default=False, nullable=False)

    skills = db.relationship('Skill', secondary='candidate_skill', back_populates='candidates')

    def __repr__(self):
        return f"<Candidate {self.full_name}>"


class Employer(db.Model):
    __tablename__ = 'employer'

    employer_id = db.Column('EmployerID', db.Integer, primary_key=True)
    company_name = db.Column('CompanyName', db.String(120), nullable=False)
    contact_email = db.Column('ContactEmail', db.String(120), unique=True, nullable=False)
    industry = db.Column('Industry', db.String(120), nullable=True)

    job_postings = db.relationship('JobPosting', back_populates='employer', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Employer {self.company_name}>"


class JobPosting(db.Model):
    __tablename__ = 'job_posting'

    job_id = db.Column('JobID', db.Integer, primary_key=True)
    employer_id = db.Column('EmployerID', db.Integer, db.ForeignKey('employer.EmployerID'), nullable=False)
    job_title = db.Column('JobTitle', db.String(120), nullable=False)
    job_description = db.Column('JobDescription', db.Text, nullable=False)
    required_education = db.Column('RequiredEducation', db.String(120), nullable=True)
    required_experience = db.Column('RequiredExperience', db.Integer, nullable=True)
    work_mode = db.Column('WorkMode', db.String(50), nullable=True)
    location = db.Column('Location', db.String(120), nullable=True)

    employer = db.relationship('Employer', back_populates='job_postings')
    skills = db.relationship('Skill', secondary='job_skill', back_populates='job_postings')

    def __repr__(self):
        return f"<JobPosting {self.job_title}>"


class Skill(db.Model):
    __tablename__ = 'skill'

    skill_id = db.Column('SkillID', db.Integer, primary_key=True)
    skill_name = db.Column('SkillName', db.String(120), unique=True, nullable=False)

    candidates = db.relationship('Candidate', secondary='candidate_skill', back_populates='skills')
    job_postings = db.relationship('JobPosting', secondary='job_skill', back_populates='skills')

    def __repr__(self):
        return f"<Skill {self.skill_name}>"


class CandidateSkill(db.Model):
    __tablename__ = 'candidate_skill'

    candidate_id = db.Column('CandidateID', db.Integer, db.ForeignKey('candidate.CandidateID'), primary_key=True)
    skill_id = db.Column('SkillID', db.Integer, db.ForeignKey('skill.SkillID'), primary_key=True)


class JobSkill(db.Model):
    __tablename__ = 'job_skill'

    job_id = db.Column('JobID', db.Integer, db.ForeignKey('job_posting.JobID'), primary_key=True)
    skill_id = db.Column('SkillID', db.Integer, db.ForeignKey('skill.SkillID'), primary_key=True)