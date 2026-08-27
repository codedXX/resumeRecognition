## Context

See proposal.md for the motivation. The workbench keeps its active batch identifier in frontend state. After a batch is started, the upload API correctly rejects further files for that identifier. Runtime batches currently retain result records and evidence until the configured terminal-batch retention period elapses; extracted resume text is already cleared after each evaluation.

## Goals / Non-Goals

**Goals:**

- Give completed and expired batches an explicit, privacy-conscious path into a new upload-and-evaluate cycle.
- Release the prior batch's remaining runtime data as soon as the user starts that next cycle.
- Make the 5-file selection and 10 MB single-file limits visible before file selection and consistent with validation.

**Non-Goals:**

- Preserve or export previous evaluation results across cycles.
- Cancel, restart, or delete an evaluation that is pending or processing.
- Change accepted file formats, the configured backend limits, or the normal retention cleanup for abandoned batches.

## Decisions

### Use a terminal-batch deletion API as the reset boundary

Add a batch-deletion operation that removes only batches in `completed` or `expired` state. The frontend's “开始新一轮评估” command calls it before clearing its local batch, result, selection, filter, and feedback state. A successful reset leaves the client without a batch identifier; the existing lazy batch-creation flow creates a fresh pending batch when the user next selects valid files.

This removes data from the actual memory owner instead of merely hiding prior results in the browser. A client-only reset was considered but rejected because prior evaluations and evidence would remain in the runtime store until timeout.

### Treat the explicit command as the discard acknowledgement

The reset control is shown only for completed and expired batches and uses wording that describes beginning a new cycle. Activating it intentionally discards the visible prior results; no additional confirmation dialog is added so repeated assessment remains quick.

An automatic reset on completion was considered but rejected because it would remove the results before the recruiter can review them.

### Present immutable, red limit copy at the upload entry point

Render the two Chinese limit statements directly in the drop zone and apply the established error/red token to each statement. The displayed `10 MB` represents the existing 10 MiB validation threshold using the product-facing decimal unit; validation behavior and feedback dialog continue to use the configured byte limit.

Relying only on the error dialog was considered but rejected because it provides feedback after, rather than before, an invalid selection.

## Risks / Trade-offs

- [A reset irreversibly removes review results] → expose it only as a deliberate terminal-state command with clear wording; existing retention behavior remains available until that command is used.
- [A stale frontend request could race with reset] → disable the command while reset is pending, clear/invalidate batch-scoped queries after success, and make the backend state check authoritative.
- [Displayed and configured limits could diverge later] → derive UI values from the existing frontend constants and retain backend validation as the final authority.

## Migration Plan

1. Deploy the deletion endpoint and its terminal-state safeguards before or together with the frontend command.
2. Deploy the frontend reset flow and visible limit copy.
3. Roll back by removing the frontend command; the existing runtime retention cleanup continues to handle batches. The deletion endpoint can remain unused without affecting existing uploads or evaluations.
