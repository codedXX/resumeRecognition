## Purpose

让一次简历分析只在单个 FastAPI 进程的内存生命周期内存在，不再把简历原文、批次、评分或证据 Diff 写入数据库，同时保留当前上传、异步评估和结果展示流程。

## ADDED Requirements

### Requirement: Volatile analysis lifecycle

The system SHALL keep analysis batches, temporary extracted text, evaluation statuses, scores, reasons, and evidence in process memory only, and SHALL never persist them to SQLite, another database, or a frontend static file.

#### Scenario: Recruiter uploads and starts an analysis

- **WHEN** a recruiter uploads supported resumes and starts evaluation for a selected role
- **THEN** the system parses and evaluates the files using in-memory state
- **AND** the original PDF/DOCX bytes and extracted text are not written to persistent storage

#### Scenario: Recruiter polls an active analysis

- **WHEN** the frontend requests batch status or candidate results while evaluation is active or has just completed
- **THEN** the API returns the current in-memory status and result using the existing response shapes
- **AND** the selected role rules are represented by an immutable snapshot for that batch

### Requirement: No durable result history

The system SHALL make no promise to restore active batches, scores, reasons, or evidence after process termination and SHALL remove terminal in-memory analysis state after a bounded cleanup window.

#### Scenario: Backend process restarts

- **WHEN** the backend process is restarted or replaced
- **THEN** previously active and completed analysis data is unavailable
- **AND** persisted role rules remain available from the role configuration file

#### Scenario: Terminal analysis reaches cleanup

- **WHEN** a completed, failed, or expired analysis exceeds the configured in-memory retention window
- **THEN** its batch metadata, extracted text, scores, reasons, and evidence are removed from memory
- **AND** later requests receive the existing not-found or expired response instead of historical results

### Requirement: Single-process runtime boundary

The system SHALL document and enforce a single-worker runtime for volatile analysis state and SHALL not claim cross-worker or cross-instance consistency.

#### Scenario: Deployment starts with multiple workers

- **WHEN** the service is configured with more than one worker while using the volatile runtime
- **THEN** startup or deployment validation reports that the configuration is unsupported
- **AND** the supported local mode runs one worker so upload, polling, and evaluation share one memory store

