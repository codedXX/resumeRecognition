## Purpose

为招聘人员提供一个清晰的批量评估工作台，用于启动选定岗位的评估、跟踪处理状态，并基于证据审阅候选人结果。

## ADDED Requirements

### Requirement: Evaluation workbench
The system SHALL provide a workbench that shows the pending files, selected job profile, and a clear action that starts the evaluation batch.

#### Scenario: Start an evaluation batch
- **WHEN** a user has selected a job profile and at least one ready resume and activates the start action
- **THEN** the system creates an evaluation batch using the selected profile snapshot and begins evaluating only the ready resumes

#### Scenario: Prevent incomplete batch start
- **WHEN** a user attempts to start evaluation without a selected job profile or without any ready resumes
- **THEN** the system prevents the start and explains what is missing

### Requirement: Batch status visibility
The system SHALL display the current count of pending, processing, completed, and failed resumes for a started batch until all eligible resumes reach a terminal state.

#### Scenario: Review in-progress batch status
- **WHEN** one or more resumes are still being processed
- **THEN** the workbench displays the completed count and the processing count for the batch

### Requirement: Evidence-first result review
The system SHALL display each completed candidate's name or source filename, score, passing score, qualified or unqualified status, and explanation. It SHALL support filtering results by qualified, unqualified, failed, and score range.

#### Scenario: Filter qualified candidates
- **WHEN** a user filters a completed batch to qualified candidates
- **THEN** the results list displays only candidates marked qualified

#### Scenario: Inspect a candidate's assessment
- **WHEN** a user opens a completed candidate result
- **THEN** the system displays the assessment reasons, requirement findings, source evidence, and criteria snapshot
