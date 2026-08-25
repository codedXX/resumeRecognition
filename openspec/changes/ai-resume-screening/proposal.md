## Why

Recruiters need a consistent way to review many PDF and Word resumes against the requirements of a specific role. Manual comparison is slow and hard to audit; an AI-assisted first-pass review can surface evidence, a score, and clear reasons for a recruiter to make the final decision.

## What Changes

- Add a recruiter-facing workspace for uploading a batch of PDF and DOCX resumes, selecting a role, and explicitly starting an evaluation.
- Add user-managed role profiles: users can create, view, edit, and delete roles, their individual requirements, the evaluation prompt, and a passing-score threshold. A new role defaults to 80, while every role may use a different threshold.
- Extract resume text and evaluate each resume with an AgentScope-powered AI workflow using the selected role's saved requirements and prompt.
- Show a 0–100 score, pass/fail status derived from the role threshold, satisfied requirements, unmet requirements, and evidence-based explanations for every evaluated candidate.
- Preserve the role-rule and prompt version used by an evaluation so historical decisions can be understood and reproduced. AI output is an initial recommendation; recruiters remain responsible for final hiring decisions.
- Provide a distinct, responsive review interface rather than a generic administration dashboard, centered on the assessment evidence behind each decision.

## Capabilities

### New Capabilities

- `job-profiles`: Manage job roles, their editable requirements, evaluation prompts, and role-level passing thresholds.
- `resume-ingestion`: Accept batches of PDF and DOCX resumes, extract usable text, and report per-file readiness or parsing failure.
- `candidate-evaluation`: Evaluate a resume against a selected job profile, calculate a score and pass/fail outcome, and retain explainable, versioned evaluation evidence.
- `screening-workbench`: Let recruiters start an uploaded batch deliberately and review its progress, results, filters, and per-candidate reasons.

### Modified Capabilities

- None.

## Impact

- `backend/`: FastAPI endpoints, persistence models, file storage, a background job mechanism, AgentScope integration, and PDF/DOCX parsers. Scanned PDFs require a later OCR extension.
- `frontend/`: React/TypeScript workspace with the evidence-first review interface.
- A configured LLM provider for structured evaluation results shared through backend configuration.
