## Why

Selecting too many resumes at once can create an unexpectedly large upload and evaluation workload. The interface needs to make the per-selection limit explicit and explain the failure before any upload begins.

## What Changes

- Limit a single frontend file-selection action to five files.
- Reject an over-limit selection as a whole: do not create a batch or send any upload request.
- Reuse the existing upload feedback dialog to state the five-file limit and the number of files selected, and let the user select files again.
- Preserve the current behaviour for selections of one to five files, including file type and size validation.

## Capabilities

### New Capabilities
- `upload-selection-validation`: Validate the number of files in one frontend selection and provide actionable feedback before upload.

### Modified Capabilities

- None.

## Impact

- Affects frontend upload preflight logic, upload feedback dialog content, and frontend tests.
- Does not change the backend upload API or impose a cumulative per-batch file limit.
