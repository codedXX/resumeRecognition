## Context

The current FastAPI upload handler already receives the entire document in memory and extracts text before a file becomes ready, but it then writes the original bytes to `UPLOAD_DIR` and stores the extracted text in `resume_files`. The background evaluator reads that database text, while the raw `storage_key` is never needed by the evaluator or exposed through the API. See `proposal.md` for the privacy motivation and `specs/resume-ingestion/spec.md` for the behavior contract.

The existing workbench needs the score, status, reason, and evidence snippets after evaluation, so this change removes source-document persistence without removing the review result. The service remains a small in-process FastAPI worker and must not introduce a second storage service just to hold transient input.

## Goals / Non-Goals

**Goals:**

- Ensure newly uploaded PDF/DOCX bytes are parsed from memory and never written to local or externally accessible file storage.
- Keep extracted text available to the pending/processing evaluator, then clear it independently for each file when evaluation reaches a terminal state.
- Clean up abandoned pending inputs with a deterministic, configurable policy while preserving role profiles and completed analysis results.
- Keep the existing upload, start, status, result, and evidence APIs compatible for the frontend.
- Provide a safe deployment step for binaries created by older versions.

**Non-Goals:**

- Do not remove retained scores, qualification decisions, criteria snapshots, or evidence Diff output from completed analyses.
- Do not add authentication, multi-tenant storage, OCR, a durable task queue, or an external blob-storage dependency.
- Do not make the original resume downloadable or expose a new file endpoint.

## Decisions

### Parse from request bytes and skip raw storage

Keep `extract_resume_text(filename, content)` as the parser boundary. After successful extraction, set the file metadata and temporary text directly, but do not generate a storage key or call `write_bytes`. Keep the nullable `storage_key` column for compatibility with existing rows; new rows leave it null, and `FileOut` remains unchanged because it never exposed the field.

**Alternative considered:** write the file and immediately unlink it after parsing. Rejected because a crash between write and unlink still creates a privacy window and leaves cleanup ambiguity; not writing at all is simpler and stronger.

### Store extracted text only as transient orchestration state

The current background task starts after the upload request has returned, so it needs a restart-tolerant handoff. Keep `extracted_text` in the existing database row while a batch is pending or processing, then clear it in a per-file `finally` path after either a successful evaluation or a provider/validation failure. The evaluator continues to persist score, status, reason, evidence, and provider error fields for review.

**Alternative considered:** keep the text only in an in-memory dictionary passed to the background task. Rejected because a process restart would lose pending work and the current persistence model already provides a bounded transient handoff without exposing source files.

### Use an explicit pending-input cleanup window

Replace the unused day-based raw-file retention setting with a `pending_input_retention_minutes` setting (default: 60). A cleanup helper runs at application startup and at batch API boundaries, finds pending batches older than the window, clears any extracted text, marks the batch as `expired`, and prevents it from starting. Keeping the lightweight metadata lets the existing workbench explain why a fresh upload is required without retaining resume content or adding a scheduler dependency.

**Alternative considered:** leave pending text until a daily retention job. Rejected because the product promise is analysis-only input and the existing service has no durable scheduler; a bounded opportunistic cleanup is predictable for this deployment shape.

### Preserve result evidence while limiting source retention

Do not redact or delete `Evaluation.evidence` or `reason` in this change. They are the deliberate review output required by the evidence Diff workbench, while `extracted_text` and original binaries are the source content being minimized. The UI continues to label results as AI-assisted and human-reviewed.

### Handle legacy binaries as a deployment migration

Provide a one-time cleanup operation scoped to the configured `UPLOAD_DIR`. It removes previously generated PDF/DOCX binaries and may null out their obsolete `storage_key` values, but it does not delete role profiles, batch records, criteria snapshots, evaluations, or evidence results. Rollback must not recreate or rehydrate deleted source files.

## Risks / Trade-offs

- [A process restart during evaluation can leave transient text in a processing row] → Run the same cleanup helper at startup and clear text in every terminal evaluator path; a future durable worker can reuse the lifecycle contract.
- [A recruiter may wait longer than the pending cleanup window before selecting a role] → Make the window configurable, surface an expired/abandoned-batch message, and require a fresh upload rather than silently evaluating empty text.
- [Evidence snippets and reasons can still contain personal information] → Keep them only as intentional analysis output, document that distinction, and scope a separate result-redaction policy if stricter data minimization is later required.
- [Older deployments may contain orphaned files] → Make the migration cleanup explicit, path-scoped, and verifiable before enabling the new upload path.

## Migration Plan

1. Add the transient-input lifecycle and cleanup tests before changing the handler.
2. Change new uploads to parse in memory, remove raw-file writes, clear extracted text after each terminal file state, and add pending-batch cleanup at startup/API boundaries.
3. Replace `RESUME_RETENTION_DAYS` documentation with `PENDING_INPUT_RETENTION_MINUTES`, keeping the database column nullable for compatibility.
4. Run the one-time cleanup against the configured upload directory and verify no generated resume binaries remain; retain role, batch, and analysis-result metadata.
5. Deploy and monitor upload, evaluation, and cleanup logs without logging resume text. Roll back code only if needed; do not restore deleted source binaries.
