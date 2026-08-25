## Purpose

将每份可用简历与其选定岗位的版本化标准进行可解释的 AI 初筛，为招聘人员提供一致、可复核的评估建议。

## ADDED Requirements

### Requirement: Role-specific AI evaluation
The system SHALL evaluate each ready resume against the selected job profile's captured prompt and requirements and SHALL produce a numeric score from 0 through 100.

#### Scenario: Evaluate a ready resume
- **WHEN** a user starts a batch with a selected job profile and a ready resume
- **THEN** the system produces an evaluation score and requirement-level findings using the batch's captured criteria

#### Scenario: Isolate job-profile criteria
- **WHEN** the same resume is evaluated in separate batches for two different job profiles
- **THEN** each evaluation uses only the criteria snapshot of its own selected profile

### Requirement: Configurable pass-fail determination
The system SHALL mark an evaluation as qualified when its score is greater than or equal to the selected job profile's captured passing score, and SHALL mark it unqualified when the score is lower.

#### Scenario: Score meets the threshold
- **WHEN** a resume receives a score of 80 and the captured passing score is 80
- **THEN** the system marks the candidate qualified

#### Scenario: Score is below a customized threshold
- **WHEN** a resume receives a score of 84 and the captured passing score is 85
- **THEN** the system marks the candidate unqualified

### Requirement: Explainable screening outcome
The system SHALL return a concise reason for the qualification outcome, a list of satisfied requirements, a list of unmet or insufficient requirements, and resume-derived evidence for every material finding. The system MUST identify an unavailable or failed AI evaluation rather than infer an outcome.

#### Scenario: Explain a qualified candidate
- **WHEN** an evaluation is marked qualified
- **THEN** the result shows the score, the passing score, satisfied requirements, and evidence supporting the recommendation

#### Scenario: Explain an unqualified candidate
- **WHEN** an evaluation is marked unqualified
- **THEN** the result shows the score, the passing score, unmet or insufficient requirements, and evidence supporting the gaps

#### Scenario: Handle an evaluation failure
- **WHEN** the AI evaluation cannot return a valid result
- **THEN** the system marks the resume as evaluation failed and does not assign qualified or unqualified status

### Requirement: Fair-use guardrails
The system SHALL present AI results as an initial screening recommendation and SHALL instruct the evaluator not to use protected or sensitive personal characteristics as scoring criteria or evidence.

#### Scenario: Present an AI recommendation
- **WHEN** a user views an evaluation result
- **THEN** the interface identifies the result as an AI-assisted recommendation requiring human review
