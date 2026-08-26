## Purpose

让招聘人员在一个具有纸本橙与代码审查气质的工作台中快速阅读候选人结论，并能沿着清晰的证据 Diff 轨道核对每个分数与原文依据。

## ADDED Requirements

### Requirement: Editorial paper visual language

The workbench SHALL present a restrained editorial visual language using a warm paper background, dark ink text, muted brown-gray secondary text, hairline dividers, low-radius surfaces, and a single burnt-orange accent for active review states.

#### Scenario: Recruiter opens the workbench

- **WHEN** the recruiter opens the screening workbench on desktop
- **THEN** the page presents a warm paper-toned surface with typographic hierarchy and document-like dividers rather than a generic dashboard card grid

#### Scenario: Recruiter views an active state

- **WHEN** a role, candidate, filter, or review control is active
- **THEN** the active state is expressed with the burnt-orange accent and a text or symbol label in addition to color

### Requirement: Evidence diff semantics

The workbench SHALL express evidence state with review-oriented symbols and text: `+` for satisfied requirements, `-` for missing or insufficient evidence, and `>` for the currently selected candidate or source excerpt.

#### Scenario: Candidate has satisfied and unmet requirements

- **WHEN** a candidate result contains both satisfied and unmet requirements
- **THEN** the detail view shows both groups with distinct `+` and `-` markers, plain-language labels, and no reliance on color alone

#### Scenario: Candidate has source evidence

- **WHEN** a candidate result includes a resume evidence snippet
- **THEN** the snippet is shown as a quoted source line with a visible review marker and remains visually associated with the requirement it supports

### Requirement: Three-part review structure

The workbench SHALL organize the desktop review flow into a queue or command navigation region, a candidate results region, and an evidence detail region, with the current role, batch status, score, threshold, and review state visible in context.

#### Scenario: Recruiter reviews a batch

- **WHEN** a batch has uploaded or evaluated files
- **THEN** the recruiter can see the file queue, candidate list, and selected candidate evidence without navigating away from the workbench

#### Scenario: Recruiter changes the selected candidate

- **WHEN** the recruiter selects another candidate from the results region
- **THEN** the evidence detail region updates to that candidate while preserving the role, batch, and threshold context

### Requirement: Responsive and accessible review flow

The workbench SHALL preserve the review sequence and interaction clarity at narrow widths, expose visible keyboard focus, support reduced-motion preferences, and communicate every status through text or symbols as well as color.

#### Scenario: Recruiter uses a narrow viewport

- **WHEN** the viewport cannot fit three regions side by side
- **THEN** the queue, candidate list, and evidence detail become a single-column drill-down sequence without hiding the explicit review actions

#### Scenario: Recruiter navigates with a keyboard

- **WHEN** focus moves across selectors, upload controls, filters, candidate rows, and dialog actions
- **THEN** the focused control has a visible outline and the control remains operable without a pointer

#### Scenario: Recruiter prefers reduced motion

- **WHEN** the operating system requests reduced motion
- **THEN** non-essential transitions and animations are removed or reduced while state changes remain understandable

### Requirement: Existing review behavior remains available

The visual redesign SHALL preserve the existing role management, private resume upload, explicit start-evaluation action, batch progress, result filtering, and evidence-detail behavior.

#### Scenario: Recruiter uploads before evaluation

- **WHEN** the recruiter uploads a supported PDF or DOCX without starting a batch
- **THEN** the file appears in the pending queue and no evaluation is triggered automatically

#### Scenario: Recruiter reviews a completed result

- **WHEN** an evaluation completes
- **THEN** the recruiter can filter the result, view its score and threshold, inspect requirements and evidence, and see the human-review label in the redesigned workbench
