# Career-Pilot Matching Engine Evaluation Report

Generated on: 2026-06-22 00:11:02

## Overall Metrics

| Metric | Value |
| --- | --- |
| **Total Evaluated** | 5 |
| **Accuracy** | 100.00% |
| **Precision** | 100.00% |
| **Recall** | 100.00% |
| **F1-Score** | 100.00% |
| **LLM Judge Avg Reasoning Score** | 4.50/5.0 |

### Confusion Matrix Details
- **True Positives (TP)**: 2
- **True Negatives (TN)**: 3
- **False Positives (FP)**: 0
- **False Negatives (FN)**: 0

## Detailed Test Cases

| Scenario | Job Title | Expected | Predicted | Status | Judge Score | Judge Verdict | Feedback |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Fresher AI Engineer in Kochi/Remote | Junior AI Developer (Remote) | MATCH | MATCH | ✅ True Positive | 5 | VALID | The agent's decision was accurate and logical, accurately matching the user's preferred role, location, and skills without hallucinating any details. |
| Fresher AI Engineer in Kochi/Remote | Lead Machine Learning Engineer | REJECT | REJECT | ✅ True Negative | N/A | VALID | Agent correctly rejected the job listing. |
| Fresher AI Engineer in Kochi/Remote | PHP Web Developer | REJECT | REJECT | ✅ True Negative | N/A | VALID | Agent correctly rejected the job listing. |
| Mid-Level Frontend Developer in Mumbai | React.js Frontend Engineer | MATCH | MATCH | ✅ True Positive | 4 | VALID | The agent's decision is mostly logical, but it might be better to note that the user's preferred locations include remote, which is not explicitly mentioned in the job snippet as an option. |
| Mid-Level Frontend Developer in Mumbai | Python DevOps Engineer | REJECT | REJECT | ✅ True Negative | N/A | VALID | Agent correctly rejected the job listing. |
