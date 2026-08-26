## MODIFIED Requirements

### Requirement: Batch resume upload
The system SHALL let a user add multiple resume files to a pending batch before evaluation begins. The system MUST accept PDF and DOCX files, MUST reject unsupported file types without preventing other valid files from being added, and MUST NOT persist the original uploaded binary after the request has been processed.

#### Scenario: Add supported resume files
- **WHEN** a user selects one or more PDF or DOCX files
- **THEN** the system extracts each file's text, adds it to the pending batch with its filename and preparation status, and does not create a raw file in the configured upload directory

#### Scenario: Reject an unsupported file
- **WHEN** a user selects a file whose format is neither PDF nor DOCX
- **THEN** the system marks that file as unsupported, does not include it in the evaluable batch, and does not persist its binary content

#### Scenario: Preserve valid files in a mixed upload
- **WHEN** a user selects both supported and unsupported files in one request
- **THEN** the system reports the unsupported files independently while keeping valid files available for the explicit evaluation action, without persisting any uploaded binary

### Requirement: Resume text preparation
The system SHALL extract text from each accepted resume before it is evaluated and SHALL show a per-file failure state when no usable text can be extracted. Extracted text MAY be retained only while the pending or processing batch needs it and MUST be cleared when the file reaches a terminal state.

#### Scenario: Extract text successfully
- **WHEN** an accepted resume contains extractable text
- **THEN** the system marks the resume ready for evaluation and retains only the extracted text needed for the pending or processing batch

#### Scenario: Handle an unreadable or image-only resume
- **WHEN** a PDF or DOCX cannot yield usable text
- **THEN** the system marks that file as not ready, explains that it cannot be evaluated, and does not retain extracted resume content

#### Scenario: Clear text after evaluation
- **WHEN** a ready resume reaches a terminal evaluation state, whether completed or failed
- **THEN** the system clears the temporary extracted text while retaining the file status and the analysis result data needed by the review workbench

## ADDED Requirements

### Requirement: Ephemeral analysis input lifecycle
The system SHALL treat the original resume document as an ephemeral input to one analysis batch. No newly uploaded PDF or DOCX may remain on local or externally accessible file storage after ingestion, and abandoned pending batches MUST have their temporary extracted text removed by the configured cleanup policy.

#### Scenario: Upload directory remains free of new resume binaries
- **WHEN** a supported resume upload succeeds
- **THEN** the configured upload directory contains no newly created PDF or DOCX for that upload and the API response remains usable by the existing batch workflow

#### Scenario: Abandoned pending batch is cleaned up
- **WHEN** a pending batch exceeds the configured pending-input cleanup window without starting evaluation
- **THEN** the system removes its temporary extracted text and marks the batch as no longer able to start with those inputs

#### Scenario: Legacy stored binary is removed during deployment cleanup
- **WHEN** the privacy change is deployed over an installation that has previously stored resume binaries
- **THEN** the deployment cleanup removes those legacy binaries without deleting role profiles or retained analysis results
