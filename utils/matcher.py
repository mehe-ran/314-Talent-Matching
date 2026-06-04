import difflib

def find_close_matches(keyword, possibilities, n=3, cutoff=0.6):
    return difflib.get_close_matches(keyword, possibilities, n, cutoff)

def calculate_job_recommendations(candidate, all_jobs):
    candidate_skill_ids = {skill.skill_id for skill in candidate.skills}
    
    scored_jobs = []
    for job in all_jobs:
        job_skill_ids = {skill.skill_id for skill in job.skills}
        
        # Calculate score as the number of common skills
        common_skills = candidate_skill_ids.intersection(job_skill_ids)
        score = len(common_skills)
        
        if score > 0:
            scored_jobs.append({'job': job, 'score': score})
            
    # Sort jobs by score in descending order
    sorted_jobs = sorted(scored_jobs, key=lambda x: x['score'], reverse=True)
    
    # Return just the job objects in the correct order
    return [item['job'] for item in sorted_jobs]

def calculate_candidate_recommendations(job, all_candidates):
    job_skill_ids = {skill.skill_id for skill in job.skills}

    scored_candidates = []
    for candidate in all_candidates:
        candidate_skill_ids = {skill.skill_id for skill in candidate.skills}
        
        common_skills = job_skill_ids.intersection(candidate_skill_ids)
        score = len(common_skills)
        
        if score > 0:
            scored_candidates.append({'candidate': candidate, 'score': score})
            
    sorted_candidates = sorted(scored_candidates, key=lambda x: x['score'], reverse=True)
    
    return [item['candidate'] for item in sorted_candidates]
