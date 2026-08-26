## Purpose

让小规模本地部署可以在不依赖数据库的情况下持久保存岗位规则，并继续通过现有岗位管理界面安全地创建、编辑、排序和删除规则。

## ADDED Requirements

### Requirement: Persistent role rule source

The system SHALL load active role rules from a backend-managed JSON file and SHALL keep that file separate from frontend static assets and all resume analysis data.

#### Scenario: Service starts without an existing role file

- **WHEN** the backend starts and the configured role file does not exist
- **THEN** the system creates or initializes an empty valid role collection without creating a database
- **AND** the role listing API returns an empty list rather than exposing an internal error

#### Scenario: Service lists configured roles

- **WHEN** a recruiter requests the role listing
- **THEN** the response contains the persisted non-archived roles with stable IDs, prompts, passing scores, and ordered requirements
- **AND** no resume filename, extracted text, score, or evidence data is read from or written to the role file

### Requirement: Role CRUD compatibility

The system SHALL preserve the existing role management API behavior for creating, updating, deleting, and reordering roles and requirements, including validation of required fields, score bounds, protected characteristics, and duplicate active names.

#### Scenario: Recruiter creates or edits a role

- **WHEN** a valid role or requirement change is submitted through the role management API
- **THEN** the change is validated and persisted to the role file
- **AND** a subsequent role listing returns the same change with stable identifiers and order

#### Scenario: Recruiter submits invalid or conflicting role data

- **WHEN** a role name, passing score, requirement, or protected characteristic violates the existing validation contract
- **THEN** the API returns a validation or conflict error
- **AND** the previous valid role file remains unchanged

### Requirement: Safe role file writes

The system SHALL serialize role mutations and SHALL replace the role file atomically so that concurrent edits or an interrupted write cannot leave a partially written configuration.

#### Scenario: Two recruiters save roles close together

- **WHEN** two role mutations arrive during overlapping write windows
- **THEN** each mutation is applied against a valid current role collection in a serialized order
- **AND** the role file remains valid JSON after both requests complete

#### Scenario: Role file is malformed before a write

- **WHEN** the backend detects malformed role data while loading or before applying a mutation
- **THEN** the API reports a configuration error
- **AND** the system does not silently overwrite the malformed file with an empty collection

