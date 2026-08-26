## Purpose

让招聘人员可以直接粘贴真实岗位说明，并由系统在保留原文的同时理解职责、必要条件和优先条件，避免为了使用评估而先手工拆分自然语言内容。

## ADDED Requirements

### Requirement: Complete job rule text is a first-class input

The system SHALL allow a role to be created and edited with one complete multi-line job rule text containing paragraphs, numbering, punctuation, and section headings. The saved role SHALL preserve the text content and line breaks sufficiently for later evaluation and editing.

#### Scenario: Recruiter saves a complete job description

- **WHEN** a recruiter enters a role name, passing score, and a multi-line job description containing duties and hiring requirements
- **THEN** the system accepts and persists the complete rule text
- **AND** reopening the role shows the same rule text without requiring manual splitting into individual requirement rows

#### Scenario: Empty rule text is submitted

- **WHEN** a recruiter submits a role without any usable rule text
- **THEN** the system rejects the role with a clear validation message
- **AND** it does not create a role with an empty evaluation contract

### Requirement: Natural-language rules guide structured evaluation

The system SHALL provide the complete role rule text to the evaluation provider and SHALL require the provider to distinguish job duties from candidate qualifications, including necessary conditions, preferred conditions, and ambiguous soft preferences. The final qualification decision SHALL continue to use the configured passing score and evidence from the resume rather than model prose alone.

#### Scenario: Rules contain duties and hiring requirements in one paragraph

- **WHEN** a role rule includes responsibilities such as e-commerce visual work and requirements such as design ability or AI workflow experience
- **THEN** the evaluation treats responsibilities as context and evaluates candidate qualifications as evidence-bearing criteria
- **AND** the result identifies satisfied criteria, unmet criteria, and supporting resume excerpts

#### Scenario: Rules contain a subjective soft preference

- **WHEN** a role rule contains a vague preference such as a personality description
- **THEN** the system does not use that preference as the sole reason to reject a candidate
- **AND** the result remains explainable through job-relevant evidence

### Requirement: Optional structured requirements remain compatible

The system SHALL allow structured requirements to be omitted for freeform roles and SHALL continue to evaluate and edit existing roles that already contain structured requirements. When both freeform text and structured requirements exist, the complete text SHALL remain authoritative context and the structured requirements SHALL act as explicit refinements.

#### Scenario: Freeform role has no manual requirement rows

- **WHEN** a recruiter starts an evaluation for a role containing only complete rule text
- **THEN** the evaluation can proceed without treating the empty manual requirement list as an empty scoring contract

#### Scenario: Existing structured role is edited

- **WHEN** a recruiter opens a role that already has structured requirements
- **THEN** those requirements remain visible and editable as optional refinements
- **AND** saving the role does not silently delete them

