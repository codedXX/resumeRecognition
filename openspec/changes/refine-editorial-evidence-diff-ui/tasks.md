## 1. Visual foundation

- [x] 1.1 Replace the current frontend color/type rules with the paper/editorial token system from `design.md`, including warm paper, ink, muted text, rule, orange, and sage tokens; verify the existing frontend build still succeeds.
- [x] 1.2 Add semantic region and state classes for the review header, queue, candidates, evidence detail, empty states, failures, and dialogs; verify each existing screen state renders without console errors.

## 2. Workbench structure

- [x] 2.1 Reshape the desktop workbench into review header, queue/command navigation, candidate results, and evidence detail regions while preserving current query and mutation behavior; verify role selection, upload, start evaluation, filters, and candidate selection still work.
- [x] 2.2 Render candidate status using explicit `+`, `-`, and `>` markers with text labels and preserve score, threshold, reason, and human-review copy; verify qualified, unqualified, failed, processing, and unreadable fixtures expose non-color status cues.
- [x] 2.3 Render evidence findings as a Diff-like source trail with gutter/line metadata, requirement labels, and quoted resume evidence; verify a completed result keeps each evidence snippet associated with its requirement.
- [x] 2.4 Restyle the role-management dialog, upload dropzone, filters, action buttons, notices, and empty states to the same paper/editorial language; verify CRUD validation and pending-batch guidance remain accessible.

## 3. Responsive and accessibility behavior

- [x] 3.1 Implement the narrow-layout drill-down from queue to candidate list to evidence detail, retaining explicit start and review actions; verify the workbench is usable at a mobile viewport without horizontal overflow.
- [x] 3.2 Add visible keyboard focus, text/symbol status redundancy, and reduced-motion behavior for controls, candidate rows, dialogs, and state transitions; verify keyboard interaction and `prefers-reduced-motion` coverage in frontend tests.

## 4. Verification and review

- [x] 4.1 Update component tests for paper tokens, Diff markers, result states, evidence association, responsive structure, and human-review labeling; verify `npm test` passes.
- [x] 4.2 Run the production build and inspect desktop/mobile screenshots against the C direction (warm paper, burnt orange, CLI/Diff semantics, three-region hierarchy); verify `npm run build` passes and record any visual follow-up.
- [x] 4.3 Run OpenSpec validation and confirm every requirement scenario is covered by an implementation or test; verify `openspec validate --change refine-editorial-evidence-diff-ui` passes.
