## 1. Terminal batch cleanup API

- [x] 1.1 Add a terminal-batch deletion endpoint that removes only completed or expired runtime batches, and verify API tests confirm files, evaluations, criteria snapshots, and evidence are no longer retrievable after deletion.
- [x] 1.2 Reject deletion requests for pending and processing batches without mutating their data, and verify API tests cover both protected states and the returned conflict response.

## 2. New evaluation cycle workflow

- [x] 2.1 Add the batch-deletion client operation and a completed/expired-only “开始新一轮评估” workbench action; verify frontend tests assert that the action calls deletion and is absent for pending and processing batches.
- [x] 2.2 On successful reset, clear the active batch identifier, selected candidate, filters, notices, and batch-scoped query data; verify a subsequent file selection creates a fresh batch rather than uploading to the prior batch.
- [x] 2.3 Disable the reset action while its request is pending and surface a recoverable failure message when cleanup fails; verify the old results remain visible after a failed reset request.

## 3. Upload limit disclosure

- [x] 3.1 Render “单次上传上限为 5 个文件” and “单文件上限 10 MB” in the upload entry area for every empty or active queue state, and verify frontend tests locate both statements before file selection.
- [x] 3.2 Style both limit statements with the established red/error color while preserving readable layout on desktop and mobile, and verify the style or rendered class is covered by frontend tests.

## 4. Verification

- [x] 4.1 Run the backend API test suite and frontend test suite, verifying terminal cleanup, repeated evaluation, protected active batches, and both upload-limit statements pass together.
