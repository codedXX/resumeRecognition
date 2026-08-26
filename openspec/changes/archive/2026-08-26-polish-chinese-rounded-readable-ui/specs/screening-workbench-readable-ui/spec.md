## Purpose

让招聘人员在中文化、圆润且易读的证据审阅工作台中快速理解岗位、候选人状态和证据依据，同时保持纸本橙的编辑部气质与可访问交互。

## ADDED Requirements

### Requirement: Chinese interface copy

The workbench SHALL present all user-facing explanatory labels, section headings, commands, statuses, actions, notices, and empty-state guidance in Chinese. Technical file extensions PDF/DOCX, numeric values, and `+` / `-` / `>` status symbols MAY remain unchanged.

#### Scenario: Recruiter opens an empty workbench

- WHEN a recruiter opens the workbench before selecting a position or uploading a resume
- THEN every visible explanatory heading, action, notice, empty-state message, and navigation label is written in Chinese
- AND PDF, DOCX, numeric values, and status symbols remain available as technical identifiers where needed

#### Scenario: Recruiter reviews a completed candidate

- WHEN a recruiter selects a candidate with an evaluation result
- THEN the score, passing threshold, requirement labels, evidence headings, statuses, and human-review guidance are presented in Chinese
- AND the candidate's file extension and numeric result values remain unchanged

### Requirement: Rounded editorial surfaces

The workbench SHALL use a consistent layered radius treatment that softens the outer frame and interactive surfaces while preserving the visible editorial rules that separate evidence regions.

#### Scenario: Recruiter views the desktop workbench

- WHEN the workbench is rendered at a desktop viewport
- THEN the outer workbench frame and its major regions have visibly rounded corners with consistent spacing
- AND internal dividers and editorial rules remain visible without creating unintended double borders

#### Scenario: Recruiter uses upload, filter, and management controls

- WHEN the recruiter interacts with the upload area, buttons, filters, fields, or position-management dialog
- THEN each interactive surface has a rounded shape appropriate to its hierarchy and retains a clear hover, focus, disabled, and active state

### Requirement: Readable Chinese typography

The workbench SHALL apply a readable type scale and font-role separation for Chinese copy, metadata, numeric scores, and status markers across desktop and mobile layouts.

#### Scenario: Recruiter reads the main review regions

- WHEN the recruiter views queue, candidate, or evidence content at the normal desktop viewport
- THEN body copy and controls use a comfortable Chinese reading size, supporting text remains legible, and candidate/file names and evidence quotations are visually prioritized
- AND numeric scores, line numbers, and status metadata remain distinguishable without forcing all copy into an emulated terminal style

#### Scenario: Recruiter reads the workbench on a mobile viewport

- WHEN the same content is rendered on a narrow viewport
- THEN text remains readable without horizontal scrolling, labels wrap or reflow without clipping, and controls retain touch-friendly hit areas

### Requirement: Preserve review behavior and accessibility

The visual refinement SHALL preserve existing upload, position selection, evaluation, filtering, candidate selection, evidence display, keyboard focus, and reduced-motion behavior.

#### Scenario: Recruiter completes the existing review flow

- WHEN a recruiter selects a position, uploads a supported resume, starts evaluation, filters results, and opens a candidate
- THEN each existing action produces the same request, state transition, and evidence result as before the visual refinement

#### Scenario: Keyboard and reduced-motion users navigate the workbench

- WHEN a user navigates controls with a keyboard or has reduced motion enabled
- THEN focus indicators remain visible and ordered, interactive controls remain operable, and no new essential transition depends on animation
