## 1. Upload selection validation

- [x] 1.1 Add a frontend test that selects six valid files and verifies that an upload feedback dialog states the five-file maximum and the selected count, while no batch-creation or file-upload request is made.
- [x] 1.2 Add a shared five-file single-selection limit to the frontend upload selection handler before the existing per-file preflight and upload mutation, and verify the new focused test passes.
- [x] 1.3 Populate the existing upload feedback dialog with a selection-level failure reason, maximum, and actual selected count, while retaining the existing reselect action; verify the focused test can locate the alert dialog and reselect control.

## 2. Regression verification

- [x] 2.1 Run the affected frontend upload tests under a Node.js version supported by the repository's Vite and Vitest dependencies, and verify selections of one to five files retain the existing upload path.
- [x] 2.2 Run the frontend production build and verify it completes successfully without changing the backend upload API.
