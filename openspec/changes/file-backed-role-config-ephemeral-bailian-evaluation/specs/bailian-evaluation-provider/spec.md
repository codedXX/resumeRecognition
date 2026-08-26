## Purpose

让招聘评估可以通过现有 AgentScope 适配层调用阿里云百炼的 OpenAI 兼容接口，并以可验证的结构化结果生成分数、理由、满足条件、待补证据和原文引用。

## ADDED Requirements

### Requirement: Bailian provider configuration

The system SHALL configure the Bailian provider exclusively from backend environment settings for the API key, model name, and regional or workspace-specific OpenAI-compatible base URL, and SHALL never expose the key to the frontend or source repository.

#### Scenario: Bailian evaluation is enabled with complete configuration

- **WHEN** the provider is selected and the required key, model, and base URL settings are present
- **THEN** the backend initializes the AI provider with those settings
- **AND** the frontend can continue using the existing upload and evaluation API without receiving the secret

#### Scenario: Bailian evaluation is enabled with incomplete configuration

- **WHEN** the provider is selected but a required setting is missing or invalid
- **THEN** the backend reports a clear configuration error before starting an evaluation
- **AND** no request is sent to an undefined or fallback external endpoint

### Requirement: Structured resume evaluation

The provider SHALL send the selected role snapshot and extracted resume text to Bailian and SHALL validate the response against the application evaluation contract before exposing it as a candidate result.

#### Scenario: Bailian returns a valid structured result

- **WHEN** Bailian returns a score from 0 to 100, a non-empty reason, and valid satisfied, unmet, and evidence fields
- **THEN** the system accepts the result after schema validation
- **AND** the application, not model prose, compares the score with the role snapshot passing score to determine qualification

#### Scenario: Bailian returns malformed or unsupported output

- **WHEN** the model returns non-JSON text, an invalid schema, an out-of-range score, or no usable response
- **THEN** the affected file is marked as a failed evaluation with a user-safe error
- **AND** other files in the same batch continue independently

### Requirement: Resume privacy during external evaluation

The system SHALL treat extracted resume text as sensitive outbound data, SHALL avoid logging API keys or resume content, and SHALL communicate that enabling Bailian sends the current analysis text to Alibaba Cloud.

#### Scenario: Recruiter enables Bailian analysis

- **WHEN** a recruiter starts an analysis using the Bailian provider
- **THEN** the product presents or documents the external-processing notice before or alongside the analysis flow
- **AND** only the current role snapshot and current resume text needed for evaluation are sent

#### Scenario: Provider request or response is logged

- **WHEN** provider diagnostics are recorded
- **THEN** logs contain provider status and safe error metadata only
- **AND** logs do not contain API keys, full resume text, or full evidence excerpts

