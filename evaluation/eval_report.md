# Career-Pilot Matching Engine Evaluation Report

Generated on: 2026-07-05 13:20:36

## Overall Metrics

| Metric | Value |
| --- | --- |
| **Total Evaluated** | 5 |
| **Accuracy** | 80.00% |
| **Precision** | 66.67% |
| **Recall** | 100.00% |
| **F1-Score** | 80.00% |
| **LLM Judge Avg Reasoning Score** | 4.67/5.0 |

### Confusion Matrix Details
- **True Positives (TP)**: 2
- **True Negatives (TN)**: 2
- **False Positives (FP)**: 1
- **False Negatives (FN)**: 0

## Detailed Test Cases

| Scenario | Job Title | Expected | Predicted | Status | Judge Score | Judge Verdict | Feedback |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fresher AI Engineer in Kochi/Remote | Junior AI Developer (Remote) | MATCH | MATCH | ✅ True Positive | 5 | VALID | The agent provided a clear and accurate explanation for the match, demonstrating a strong understanding of the candidate's profile and job requirements. |
| Fresher AI Engineer in Kochi/Remote | Lead Machine Learning Engineer | REJECT | REJECT | ✅ True Negative | N/A | VALID | Agent correctly rejected the job listing. |
| Fresher AI Engineer in Kochi/Remote | PHP Web Developer | REJECT | REJECT | ✅ True Negative | N/A | VALID | Agent correctly rejected the job listing. |
| Mid-Level Frontend Developer in Mumbai | React.js Frontend Engineer | MATCH | MATCH | ✅ True Positive | 5 | VALID | The agent's decision accurately aligns with the candidate's preferences and job requirements, providing a solid reasoning for the match. |
| Mid-Level Frontend Developer in Mumbai | Python DevOps Engineer | REJECT | MATCH | ❌ False Positive | 4 | INVALID | The agent incorrectly assumed the candidate's skills are too distant from the required skills, and also inaccurately stated the experience requirement. A more accurate assessment would focus on the lack of Python skills. |
