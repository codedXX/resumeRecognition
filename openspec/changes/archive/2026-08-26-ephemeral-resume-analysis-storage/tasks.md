## 1. Privacy lifecycle tests

- [x] 1.1 Add backend tests that upload readable PDF/DOCX fixtures and assert the response remains usable while the configured upload directory receives no new resume binary; verify the tests fail against the current `write_bytes` behavior before implementation.
- [x] 1.2 Add backend tests for completed and failed evaluations that assert `extracted_text` is cleared while score/status/reason/evidence results remain available; verify both terminal paths are covered.
- [x] 1.3 Add backend tests for an over-age pending batch that assert temporary text is cleared, the batch becomes `expired`, and a later start attempt is rejected; verify the cleanup window is configurable.

## 2. Ephemeral ingestion and evaluation implementation

- [x] 2.1 Replace the unused raw-file retention setting with `pending_input_retention_minutes`, keep the nullable storage metadata backward-compatible, and verify settings load from the environment with the documented default.
- [x] 2.2 Update the upload handler to parse accepted bytes in memory, leave `storage_key` null for new uploads, and preserve mixed-file and parser-error behavior; verify the privacy upload tests pass.
- [x] 2.3 Clear each file's temporary `extracted_text` in the evaluator after success or provider failure without changing retained evaluation result fields; verify the terminal-state tests pass for multi-file batches.
- [x] 2.4 Implement startup and batch-boundary cleanup for stale pending batches, marking them `expired` and preventing evaluation without retaining extracted text; verify cleanup is idempotent and does not alter roles or completed results.

## 3. API and workbench compatibility

- [x] 3.1 Preserve the existing upload, batch, and result response shapes while documenting null storage keys and expired-batch behavior; verify API contract tests and OpenAPI startup validation pass.
- [x] 3.2 Add frontend handling for an expired pending batch so the queue explains that a fresh upload is required and the start action cannot run with purged input; verify the component test covers the message and disabled action.

## 4. Legacy cleanup and documentation

- [x] 4.1 Add a path-scoped one-time cleanup command or startup migration for binaries previously written under `UPLOAD_DIR`, nulling obsolete storage keys without deleting analysis metadata; verify it removes only generated resume binaries in a fixture directory.
- [x] 4.2 Update `.env.example` and `README.md` to describe non-persistent source uploads, temporary extracted-text cleanup, the pending-input window, and retained analysis results; verify no documentation advertises indefinite raw-file retention.

## 5. Verification

- [x] 5.1 Run the complete backend test suite and verify upload, mixed-file, unreadable, evaluation failure, cleanup, and legacy-migration scenarios pass.
- [x] 5.2 Run the frontend test suite and production build, then verify the existing paper-orange evidence Diff still displays retained score, reason, and evidence after source cleanup.
- [x] 5.3 Run strict OpenSpec validation for `ephemeral-resume-analysis-storage` and confirm every requirement scenario is covered by an implementation or test.
