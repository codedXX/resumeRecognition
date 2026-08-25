## Purpose

让招聘人员维护不同岗位的筛选规则、提示词和合格线，使每次简历评估都使用明确且可追溯的岗位标准。

## ADDED Requirements

### Requirement: User-managed job profiles
The system SHALL let an authorized user create, view, edit, and delete job profiles. A job profile MUST include a unique display name, an evaluation prompt, a passing score, and zero or more requirements.

#### Scenario: Create a job profile with default passing score
- **WHEN** a user creates a job profile without specifying a passing score
- **THEN** the system saves the profile with a passing score of 80

#### Scenario: Update a job profile
- **WHEN** a user changes a job profile's name, prompt, or passing score to a value from 0 through 100
- **THEN** the system persists the new values for subsequent evaluations

#### Scenario: Reject an invalid passing score
- **WHEN** a user saves a passing score outside the 0 through 100 range
- **THEN** the system rejects the change and identifies the invalid field

#### Scenario: Delete a job profile
- **WHEN** a user confirms deletion of a job profile that has no evaluation history
- **THEN** the system removes the profile from the available-role list

### Requirement: User-managed role requirements
The system SHALL let a user add, view, edit, reorder, and delete individual requirements within a job profile. Each requirement MUST have a description and MAY include a priority or scoring guidance.

#### Scenario: Add a role requirement
- **WHEN** a user adds a requirement to a job profile and saves it
- **THEN** the requirement appears in that profile and is included in future evaluations

#### Scenario: Modify a role requirement
- **WHEN** a user edits an existing requirement
- **THEN** subsequent evaluations use the edited requirement without changing prior evaluation records

#### Scenario: Remove a role requirement
- **WHEN** a user removes a requirement from a job profile
- **THEN** the requirement is absent from subsequent evaluations and remains visible only in historical evaluation snapshots where it was used

### Requirement: Versioned evaluation criteria
The system SHALL retain an immutable snapshot of a job profile's name, requirements, prompt, and passing score whenever an evaluation batch starts.

#### Scenario: Preserve a batch's criteria
- **WHEN** a user starts an evaluation batch and later edits the selected job profile
- **THEN** the completed batch continues to display the criteria snapshot captured when it started
