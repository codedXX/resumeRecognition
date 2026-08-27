## Context

The frontend already validates each selected file for extension and size before invoking the upload mutation. Existing validation failures are presented through a reusable upload feedback dialog. See `proposal.md` for the motivation and `specs/upload-selection-validation/spec.md` for the behavioural contract.

## Goals / Non-Goals

**Goals:**
- Stop an over-limit selection before the upload mutation can create a batch or submit files.
- Present the count failure through the existing feedback dialog and preserve its reselect action.
- Keep all selections containing one to five files on the current validation and upload path.

**Non-Goals:**
- Enforcing a cumulative maximum across multiple selections in the same batch.
- Adding a server-side upload-count restriction or changing the upload API.
- Changing file type or per-file size limits.

## Decisions

### Validate the selection count before per-file preflight and mutation

The selection handler will compare the selected file count with a shared maximum of five before calling the per-file validator or upload mutation. This prevents both batch creation and upload requests for an invalid selection.

An alternative is to retain the first five files and upload them. It was rejected because users would receive a partial, surprising result and could miss resumes without noticing.

### Represent the count failure in the existing upload feedback flow

The over-limit result will populate the existing feedback state with a clear failure reason and detail containing both the allowed maximum and selected count. The current modal already supplies an alert-dialog role, a close action, and a reselect action, so reusing it preserves accessibility and interaction consistency.

An alternative is a separate count-limit modal. It was rejected because it duplicates feedback UI and introduces a second failure-handling path.

## Risks / Trade-offs

- [Frontend-only enforcement can be bypassed by non-UI clients] → This change is intentionally scoped to a single frontend selection; backend policy remains unchanged.
- [The failure summary is not tied to one file] → The dialog copy will explicitly describe the selection as a whole and include the selected count.
- [Future changes could introduce another selection entry point] → The count guard belongs in the shared file-selection handler, which covers the current input and reselect flow.

## Migration Plan

Deploy with the frontend release. No data migration or backend rollout is required. Rollback consists of restoring the prior frontend build, because rejected selections do not create server-side data.
