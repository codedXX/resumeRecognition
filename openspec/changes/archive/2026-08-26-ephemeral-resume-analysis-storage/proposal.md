## Why

Uploaded resumes contain personal information, but the current ingestion path writes every readable PDF/DOCX to `UPLOAD_DIR` and never removes it. The product should use the original document only as input to the requested analysis, while still allowing the recruiter to review the resulting score and evidence Diff.

## What Changes

- Stop persisting uploaded PDF/DOCX binaries; parse accepted files from the request bytes and leave `storage_key` empty.
- Treat extracted resume text as evaluation input only: retain it while a pending/processing batch needs it, then clear it when the file reaches a terminal state.
- Preserve batch metadata, scores, qualification status, reasons, and evidence Diff output so the recruiter can review the completed analysis.
- Add deterministic cleanup for abandoned pending batches and failed evaluation paths so temporary extracted text is not left indefinitely.
- Remove the unused fixed-day raw-file retention assumption from configuration and deployment documentation.
- Add backend tests proving supported uploads do not create files in the upload directory and temporary text is cleared after evaluation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `resume-ingestion`: define uploaded resume binaries as non-persistent analysis inputs and define the lifecycle of extracted text for pending, processing, and terminal file states.

## Impact

- Affects `backend/app/main.py`, ingestion/storage configuration, persistence models, cleanup orchestration, and backend API tests.
- The upload API response remains compatible for the frontend; `storage_key` becomes null for newly uploaded files.
- Existing evaluation result APIs and the paper-orange evidence Diff remain available because score, status, reason, and evidence result data are retained.
- Existing raw files created by older versions need a one-time deployment cleanup; no migration is required for the nullable `storage_key` field.
