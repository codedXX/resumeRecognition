## Purpose

此能力让招聘人员在审阅完成后开始新的简历评估轮次，同时及时清除上一轮仅用于本次分析的临时结果和证据数据。

## ADDED Requirements

### Requirement: Start a new evaluation cycle from a terminal batch
The system SHALL allow a user to start a new evaluation cycle when the current batch is completed or expired. Starting a new cycle MUST remove the current batch from runtime storage and reset the workbench to an empty upload queue; subsequent file selection MUST be uploaded as a new batch.

#### Scenario: Start a new cycle after reviewing completed results
- **WHEN** a user activates the new-evaluation action for a completed batch
- **THEN** the system removes that batch's files, evaluations, criteria snapshot, and evidence from runtime storage and displays an empty upload queue with no prior candidate results selected or listed

#### Scenario: Upload after starting a new cycle
- **WHEN** a user starts a new evaluation cycle and then selects one to five valid files
- **THEN** the system creates a new pending batch and accepts the files without attempting to upload them to the prior completed batch

### Requirement: Protect active evaluation batches from reset
The system MUST NOT offer the new-evaluation action for pending or processing batches, and it MUST reject any attempt to remove a batch that is not completed or expired.

#### Scenario: Evaluation is still processing
- **WHEN** a batch is processing one or more resumes
- **THEN** the workbench keeps the current batch and does not present an action that clears its data

#### Scenario: Invalid reset request
- **WHEN** a client attempts to remove a pending or processing batch
- **THEN** the system rejects the request and preserves the batch and its runtime data
