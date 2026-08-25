## Purpose

让招聘人员可靠地提交一批常见格式的简历，并在评估前看到每个文件是否已成功提取可用的文本内容。

## ADDED Requirements

### Requirement: Batch resume upload
The system SHALL let a user add multiple resume files to a pending batch before evaluation begins. The system MUST accept PDF and DOCX files and MUST reject unsupported file types without preventing other valid files from being added.

#### Scenario: Add supported resume files
- **WHEN** a user selects one or more PDF or DOCX files
- **THEN** the system adds each file to the pending batch with its filename and preparation status

#### Scenario: Reject an unsupported file
- **WHEN** a user selects a file whose format is neither PDF nor DOCX
- **THEN** the system marks that file as unsupported and does not include it in the evaluable batch

### Requirement: Resume text preparation
The system SHALL extract text from each accepted resume before it is evaluated and SHALL show a per-file failure state when no usable text can be extracted.

#### Scenario: Extract text successfully
- **WHEN** an accepted resume contains extractable text
- **THEN** the system marks the resume ready for evaluation

#### Scenario: Handle an unreadable or image-only resume
- **WHEN** a PDF or DOCX cannot yield usable text
- **THEN** the system marks that file as not ready, explains that it cannot be evaluated, and permits the remaining ready files to proceed

### Requirement: Explicit evaluation start
The system MUST NOT evaluate a pending batch solely because files were uploaded. It SHALL require the user to select a job profile and explicitly start the evaluation.

#### Scenario: Upload without evaluation
- **WHEN** a user finishes uploading resumes but has not selected a role and started evaluation
- **THEN** the system retains the pending batch without calling the evaluation workflow
