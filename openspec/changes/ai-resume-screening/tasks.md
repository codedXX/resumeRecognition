All browser-client work in this checklist belongs in `frontend/`; all FastAPI, AgentScope, parsing, persistence, migration, and API-test work belongs in `backend/`.

## 1. Project foundation

- [x] 1.1 Create the `backend/` FastAPI application structure, configuration model, dependency management, and health endpoint; verify the service starts and its health check returns success.
- [x] 1.2 Create the `frontend/` React, TypeScript, and Vite client with Tailwind, accessible primitive, query-state, and table dependencies; verify the production client build succeeds.
- [x] 1.3 Define the relational schema and migrations under `backend/` for role profiles, ordered requirements, batches, resume files, criteria snapshots, and evaluations; verify migrations run against an empty database.

## 2. Role profile and criteria management

- [x] 2.1 Implement persistence and API validation for role profiles, including a 0–100 passing score that defaults to 80; verify API tests cover create, read, update, invalid score, and delete behavior.
- [x] 2.2 Implement CRUD operations for ordered requirements within a role profile; verify API tests show edits apply only to future evaluations.
- [x] 2.3 Implement immutable criteria snapshot creation when a batch starts and archive-safe role deletion behavior; verify a profile edit after batch creation does not change the stored snapshot.

## 3. Resume ingestion

- [x] 3.1 Implement validated private file storage and upload APIs for batches of PDF and DOCX files; verify supported files are accepted and an unsupported file is rejected without blocking valid files.
- [x] 3.2 Implement PDF and DOCX text-extraction adapters and per-file preparation states; verify fixtures cover readable PDF, readable DOCX, and unreadable/image-only input.
- [x] 3.3 Implement pending-batch behavior that requires an explicit selected role and start action; verify upload alone never invokes an evaluation call.

## 4. AI evaluation workflow

- [x] 4.1 Configure an AgentScope-backed evaluation adapter with provider settings kept outside source control; verify a mocked provider can be invoked through the adapter.
- [x] 4.2 Define and validate the structured evaluation result contract: score, requirement findings, evidence snippets, outcome reason, and error state; verify malformed model output is rejected and retried only within the configured bound.
- [x] 4.3 Implement evaluation orchestration using each batch's criteria snapshot, with independent per-file state persistence; verify a failed file does not prevent another ready file from completing.
- [x] 4.4 Implement deterministic qualified/unqualified status calculation from score and captured threshold; verify boundary cases for 80/80 and 84/85 pass.
- [x] 4.5 Add prompt guardrails and result labeling for AI-assisted, evidence-based human review; verify protected-characteristic instructions cannot be included as evaluation criteria.

## 5. Batch status and result APIs

- [x] 5.1 Implement explicit batch-start, batch-status, and candidate-result APIs with aggregate counts and terminal error states; verify integration tests cover processing, completion, unreadable, and failed outcomes.
- [x] 5.2 Implement result filtering by status and score range plus detail retrieval with criteria snapshot and evidence; verify API tests return only matching candidates and preserve historical criteria.

## 6. Recruiter workbench frontend

- [x] 6.1 Build role-profile list and editor screens with full role, prompt, requirement, and threshold CRUD; verify a new profile displays a default passing score of 80 and form errors are accessible.
- [x] 6.2 Build the pending upload queue and explicit start-evaluation interaction; verify the action remains disabled with no ready file or no selected role and gives a clear reason.
- [x] 6.3 Build the batch workbench with status counts, filters, and responsive candidate drill-down; verify a started batch updates visible progress until all eligible files reach terminal states.
- [x] 6.4 Implement the evidence-rail result detail using the approved color, type, and document-layout tokens; verify every qualification result shows the score, threshold, reasons, requirements, evidence, and AI-review label.
- [x] 6.5 Add responsive, keyboard, focus, color-independent status, and reduced-motion behavior; verify the workbench passes automated accessibility checks and is usable at mobile width.

## 7. Quality, privacy, and release readiness

- [x] 7.1 Add backend unit and integration coverage for the four capability specs; verify the full backend test suite passes.
- [x] 7.2 Add frontend component and end-to-end coverage for role CRUD, explicit evaluation start, threshold boundary, qualified result, unqualified result, unreadable file, and evaluation failure; verify the client test suite passes.
- [x] 7.3 Configure request/file limits, private storage access, log redaction, and documented provider/retention deployment settings; verify test logs contain no resume text and unauthorized file access is denied.
- [x] 7.4 Run the OpenSpec validation and a representative manual batch review; verify all change artifacts validate and the reviewer can trace every displayed outcome to captured criteria and resume evidence.
