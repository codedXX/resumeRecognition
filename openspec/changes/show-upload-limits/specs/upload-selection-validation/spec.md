## ADDED Requirements

### Requirement: Display upload selection limits
The frontend SHALL display the selection-count limit and single-file size limit in the upload entry area before the user opens the file picker. It MUST state “单次上传上限为 5 个文件” and “单文件上限 10 MB”, and visually emphasize both limit statements in red.

#### Scenario: User views an empty upload queue
- **WHEN** a user views the upload entry area before selecting files
- **THEN** the user can see both red limit statements without opening the file picker or triggering a validation error

#### Scenario: User begins another evaluation cycle
- **WHEN** a user starts a new evaluation cycle and the empty upload queue is displayed
- **THEN** the upload entry area continues to show the same two red limit statements
