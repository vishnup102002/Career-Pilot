import os
import sys
import json
import re
from datetime import datetime
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage

# Ensure parent directory is in path to import agents modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.config import llm

def run_agent_matcher(profile: Dict[str, Any], jobs: List[Dict[str, Any]]) -> str:
    """
    Simulates the scout agent matching logic on a set of jobs.
    """
    if llm is None:
        raise ValueError("LLM is not configured. Please set GROQ_API_KEY or GOOGLE_API_KEY in .env")

    # Format the candidate jobs into the JSON format expected by the scout agent
    job_candidates = []
    for job in jobs:
        job_candidates.append({
            "title": job.get("title"),
            "href": job.get("href"),
            "content": job.get("snippet")
        })
    
    scraped_text = json.dumps(job_candidates, indent=2)

    prompt = f"""
    You are a precise AI Job Matcher. Your job is to find the BEST matches between a user's profile and live job results.
    
    USER PROFILE: 
    {profile.get("resume_summary")}
    
    USER PREFERENCES:
    - Preferred Job Role: {profile.get("preferred_job")}
    - Preferred Locations: {profile.get("locations")}
    
    LIVE SEARCH JOB RESULTS:
    {scraped_text}
    
    Previously Sent Jobs (DO NOT suggest these URLs again):
    []
    
    Task: Find the top 1 to 5 jobs that are the BEST MATCH for this user.
    
    EVALUATION CRITERIA (score each job out of 5):
    1. JOB ROLE MATCH: The job title/description should be related to "{profile.get("preferred_job")}" or closely adjacent fields. Adjacent roles are acceptable.
    2. LOCATION MATCH: The job should be in one of these locations: {profile.get("locations")}, or be a remote position. If location is unclear from the snippet, still include the job.
    3. EXPERIENCE MATCH: The user's experience level should reasonably fit the job requirements. For junior/fresher candidates, jobs requiring 0-2 years experience ARE valid matches. If the snippet does not specify experience requirements, do NOT reject the job.
    4. EDUCATION MATCH: Only reject if the job explicitly requires a degree the user clearly lacks.
    5. SKILL MATCH: The user should possess most of the core technical skills mentioned in the job description.
    
    SCORING:
    - Jobs passing 4-5 criteria = STRONG MATCH (include these)
    - Jobs passing 3 criteria = POSSIBLE MATCH (include these if fewer than 3 strong matches exist)
    - Jobs passing 0-2 criteria = REJECT
    
    IMPORTANT: When the search snippet is short, be GENEROUS with your evaluation. A snippet saying "AI Engineer - Bangalore" with no other details should be treated as a possible match if role and location fit.
    
    If NO jobs pass at least 3 criteria, reply with EXACTLY: "NO STRICT MATCHES FOUND TODAY."
    
    CRITICAL URL RULE: You MUST copy the EXACT 'href' URL from the JSON data. DO NOT modify, shorten, or fabricate any URL!
    
    Format matches EXACTLY like this:
    1. [Job Title] at [Company] — [Location]
       Match Score: [e.g., 85%]
       Why it's a match: [Brief explanation of how their skills, experience, and location align]
       Apply Here: [EXACT 'href' URL from the JSON data]
    """
    
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content

def parse_agent_response(response_text: str, jobs: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Parses the agent response to extract which jobs were matched, along with their reasoning.
    """
    results = {}
    
    # If agent returned the negative string, all jobs are considered REJECTED by agent
    if "NO STRICT MATCHES FOUND TODAY" in response_text:
        for job in jobs:
            results[job["job_id"]] = {"matched": False, "reasoning": "Agent rejected all jobs."}
        return results

    # For each job, look for its URL in the response
    for job in jobs:
        url = job["href"]
        if url in response_text:
            # Attempt to extract reasoning for this specific job block
            reasoning = "N/A"
            # Split the text by job blocks and find the one containing the URL
            blocks = re.split(r'\d+\.\s+', response_text)
            for block in blocks:
                if url in block:
                    match_why = re.search(r"Why it's a match:\s*(.*?)(?=\n\s*Apply Here:|\Z)", block, re.DOTALL)
                    if match_why:
                        reasoning = match_why.group(1).strip()
                    break
            
            results[job["job_id"]] = {"matched": True, "reasoning": reasoning}
        else:
            results[job["job_id"]] = {"matched": False, "reasoning": "Excluded from matching response."}
            
    return results

def run_llm_judge(profile: Dict[str, Any], job: Dict[str, Any], agent_decision: Dict[str, Any]) -> Dict[str, Any]:
    """
    Uses the LLM-as-a-Judge to evaluate the accuracy and quality of the agent's explanation.
    """
    if llm is None:
        raise ValueError("LLM is not configured.")

    judge_prompt = f"""
    You are an independent QA Judge evaluating an AI Recruiting Agent.
    
    CANDIDATE PROFILE:
    {profile.get("resume_summary")}
    
    CANDIDATE PREFERENCES:
    - Preferred Role: {profile.get("preferred_job")}
    - Preferred Locations: {profile.get("locations")}
    
    JOB SPECIFICATION:
    - Title: {job.get("title")}
    - Company: {job.get("company")}
    - Location: {job.get("location")}
    - Snippet: {job.get("snippet")}
    
    AGENT'S DECISION:
    - Matched: {agent_decision.get("matched")}
    - Reasoning Provided: {agent_decision.get("reasoning")}
    
    Evaluate the agent's decision based on:
    1. Alignment Logic: Is the decision logical based on preferred locations, role, and skills?
    2. Reasoning Quality (if matched): Did the agent explain the match accurately without hallucinating details not present in the candidate profile or job snippet?
    
    Provide your evaluation in EXACTLY the following JSON format:
    {{
        "reasoning_score": 1-5, (integer scale where 1 is poor/hallucinated, 5 is outstanding and factual)
        "verdict": "VALID" or "INVALID", (is the agent decision logical?)
        "feedback": "1-2 sentences of critical feedback."
    }}
    Return ONLY the JSON string. Do not include markdown formatting or backticks.
    """
    
    try:
        response = llm.invoke([HumanMessage(content=judge_prompt)])
        raw = response.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(raw)
    except Exception as e:
        return {
            "reasoning_score": 0,
            "verdict": "ERROR",
            "feedback": f"Failed to run LLM Judge: {str(e)}"
        }

def main():
    print("🧪 Starting Career-Pilot Agent Evaluation Suite...\n")
    
    # 1. Load test cases
    test_cases_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_cases.json")
    if not os.path.exists(test_cases_path):
        print(f"❌ Error: Test cases file not found at {test_cases_path}")
        sys.exit(1)
        
    with open(test_cases_path, "r") as f:
        scenarios = json.load(f)
        
    print(f"Loaded {len(scenarios)} evaluation scenarios.")
    
    total_evals = 0
    true_positives = 0
    true_negatives = 0
    false_positives = 0
    false_negatives = 0
    
    judge_scores = []
    detailed_reports = []
    
    # 2. Iterate through each scenario
    for scenario in scenarios:
        name = scenario["scenario_name"]
        profile = scenario["profile"]
        jobs = scenario["jobs_to_test"]
        
        print(f"\n🎬 Running Scenario: {name}")
        print("-" * 50)
        
        try:
            # Get agent prediction
            raw_response = run_agent_matcher(profile, jobs)
            predictions = parse_agent_response(raw_response, jobs)
        except Exception as e:
            print(f"❌ Scenario failed to run: {e}")
            continue
            
        for job in jobs:
            total_evals += 1
            job_id = job["job_id"]
            expected = job["expected_match"] == "STRONG MATCH"
            predicted = predictions[job_id]["matched"]
            
            # Categorize match metrics
            if expected and predicted:
                true_positives += 1
                result_status = "✅ True Positive"
            elif not expected and not predicted:
                true_negatives += 1
                result_status = "✅ True Negative"
            elif not expected and predicted:
                false_positives += 1
                result_status = "❌ False Positive"
            else:
                false_negatives += 1
                result_status = "❌ False Negative"
                
            # Run LLM judge only if matched (to judge match reasoning)
            if predicted:
                judge_res = run_llm_judge(profile, job, predictions[job_id])
                judge_scores.append(judge_res.get("reasoning_score", 0))
            else:
                # Programmatically evaluate rejection logic (no reason for LLM judge call)
                if not expected:
                    judge_res = {
                        "reasoning_score": "N/A",
                        "verdict": "VALID",
                        "feedback": "Agent correctly rejected the job listing."
                    }
                else:
                    judge_res = {
                        "reasoning_score": "N/A",
                        "verdict": "INVALID",
                        "feedback": "Agent incorrectly rejected a qualifying job listing."
                    }
                
            detailed_reports.append({
                "scenario": name,
                "job_title": job["title"],
                "expected": "MATCH" if expected else "REJECT",
                "predicted": "MATCH" if predicted else "REJECT",
                "status": result_status,
                "reasoning_score": judge_res.get("reasoning_score", "N/A"),
                "judge_verdict": judge_res.get("verdict", "N/A"),
                "judge_feedback": judge_res.get("feedback", "")
            })
            
            print(f"-> Job: {job['title']} ({job['company']})")
            print(f"   Expected: {'MATCH' if expected else 'REJECT'} | Predicted: {'MATCH' if predicted else 'REJECT'}")
            print(f"   Status: {result_status}")
            print(f"   LLM Judge Verdict: {judge_res.get('verdict')} (Score: {judge_res.get('reasoning_score')}/5)")
            print(f"   Feedback: {judge_res.get('feedback')}\n")

    # 3. Calculate metrics
    accuracy = (true_positives + true_negatives) / total_evals if total_evals > 0 else 0
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    avg_judge_score = sum(judge_scores) / len(judge_scores) if judge_scores else 0
    
    # 4. Print Summary
    print("=" * 60)
    print("📊 EVALUATION RESULTS SUMMARY")
    print("=" * 60)
    print(f"Total Test Cases Evaluated : {total_evals}")
    print(f"Accuracy                   : {accuracy:.2%}")
    print(f"Precision                  : {precision:.2%}")
    print(f"Recall                     : {recall:.2%}")
    print(f"F1-Score                   : {f1:.2%}")
    print(f"Avg Judge Reasoning Score  : {avg_judge_score:.2f}/5.00")
    print("-" * 60)
    print(f"Confusion Matrix: [TP: {true_positives}, TN: {true_negatives}, FP: {false_positives}, FN: {false_negatives}]")
    print("=" * 60)
    
    # 5. Write report to markdown file
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_report.md")
    with open(report_path, "w") as rf:
        rf.write(f"# Career-Pilot Matching Engine Evaluation Report\n\n")
        rf.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        rf.write(f"## Overall Metrics\n\n")
        rf.write(f"| Metric | Value |\n")
        rf.write(f"| --- | --- |\n")
        rf.write(f"| **Total Evaluated** | {total_evals} |\n")
        rf.write(f"| **Accuracy** | {accuracy:.2%} |\n")
        rf.write(f"| **Precision** | {precision:.2%} |\n")
        rf.write(f"| **Recall** | {recall:.2%} |\n")
        rf.write(f"| **F1-Score** | {f1:.2%} |\n")
        rf.write(f"| **LLM Judge Avg Reasoning Score** | {avg_judge_score:.2f}/5.0 |\n\n")
        
        rf.write(f"### Confusion Matrix Details\n")
        rf.write(f"- **True Positives (TP)**: {true_positives}\n")
        rf.write(f"- **True Negatives (TN)**: {true_negatives}\n")
        rf.write(f"- **False Positives (FP)**: {false_positives}\n")
        rf.write(f"- **False Negatives (FN)**: {false_negatives}\n\n")
        
        rf.write(f"## Detailed Test Cases\n\n")
        rf.write(f"| Scenario | Job Title | Expected | Predicted | Status | Judge Score | Judge Verdict | Feedback |\n")
        rf.write(f"| --- | --- | --- | --- | --- | --- | --- | --- |\n")
        for rep in detailed_reports:
            rf.write(f"| {rep['scenario']} | {rep['job_title']} | {rep['expected']} | {rep['predicted']} | {rep['status']} | {rep['reasoning_score']} | {rep['judge_verdict']} | {rep['judge_feedback']} |\n")

    print(f"💾 Report saved successfully to: {report_path}")

if __name__ == "__main__":
    main()
