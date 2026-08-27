# upload-selection-validation Specification

## Purpose

此能力在前端上传开始前校验单次文件选择数量，阻止超过产品支持范围的批量上传，并向用户说明如何修正选择。

## Requirements

### Requirement: Limit files in one upload selection
The frontend SHALL accept at most five files from one file-selection action. A selection of one to five files SHALL continue through the existing file type and size validation flow.

#### Scenario: Selection within the limit
- **WHEN** a user selects between one and five files in one action
- **THEN** the system evaluates those files using the existing upload validation and submission flow

#### Scenario: Selection exceeds the limit
- **WHEN** a user selects more than five files in one action
- **THEN** the system SHALL reject the entire selection without creating an upload batch or sending files to the upload API

### Requirement: Explain over-limit selection failures
The frontend SHALL present an upload feedback dialog when a single selection exceeds five files. The dialog MUST state that a maximum of five files can be selected at once, show the number selected, and offer the user a way to select files again.

#### Scenario: User receives actionable feedback
- **WHEN** a user selects six files in one action
- **THEN** the feedback dialog explains the five-file maximum, identifies that six files were selected, and provides a reselect action
