import difflib

JOB_TITLE_SYNONYMS = {
    'software engineer': ['developer', 'programmer', 'swe', 'dev'],
    'frontend engineer': ['frontend developer', 'ui developer', 'ui engineer', 'front-end developer', 'front-end engineer'],
    'backend engineer': ['backend developer', 'api developer', 'back-end developer', 'back-end engineer'],
    'fullstack engineer': ['fullstack developer', 'full-stack developer', 'full-stack engineer'],
    'data scientist': ['data analyst', 'statistician'],
    'machine learning engineer': ['ml engineer', 'ai engineer', 'mle'],
    'devops engineer': ['sre', 'site reliability engineer'],
    'quality assurance engineer': ['qa engineer', 'qa tester', 'tester'],
    'mobile developer': ['android developer', 'ios developer'],
}

def get_synonyms(keyword):
    """
    Get a set of synonyms for a given keyword.
    """
    keyword = keyword.lower()
    for key, values in JOB_TITLE_SYNONYMS.items():
        if keyword == key or keyword in values:
            return set([key] + values)
    return {keyword}


def find_close_matches(keyword, possibilities, n=3, cutoff=0.6):
    return difflib.get_close_matches(keyword, possibilities, n, cutoff)

def calculate_job_recommendations(candidate, all_jobs):
    candidate_skill_ids = {skill.skill_id for skill in candidate.skills}

    if not candidate_skill_ids:
        return []

    scored_jobs = []
    for job in all_jobs:
        job_skill_ids = {skill.skill_id for skill in job.skills}

        # Skip jobs that have no skills specified
        if not job_skill_ids:
            continue

        common_skills = candidate_skill_ids.intersection(job_skill_ids)

        # Score is based on how well candidate's skills match the job's requirements
        score = (len(common_skills) / len(job_skill_ids)) * 100

        if score > 0:
            scored_jobs.append({'job': job, 'score': score})

    # Sort jobs by score in descending order
    sorted_jobs = sorted(scored_jobs, key=lambda x: x['score'], reverse=True)

    return sorted_jobs

def calculate_candidate_recommendations(job, all_candidates):
    job_skill_ids = {skill.skill_id for skill in job.skills}

    if not job_skill_ids:
        return []

    scored_candidates = []
    for candidate in all_candidates:
        candidate_skill_ids = {skill.skill_id for skill in candidate.skills}

        common_skills = job_skill_ids.intersection(candidate_skill_ids)
        score = (len(common_skills) / len(job_skill_ids)) * 100 if len(job_skill_ids) > 0 else 0

        if score > 0:
            scored_candidates.append({'candidate': candidate, 'score': score})

    sorted_candidates = sorted(scored_candidates, key=lambda x: x['score'], reverse=True)

    return sorted_candidates
