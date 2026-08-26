## Purpose

让空白初始工作台在常见桌面视口内保持稳定、无需滚动即可开始操作，同时在窗口较矮、内容增多或使用移动设备时保留可访问的自然滚动能力。

## ADDED Requirements

### Requirement: Empty desktop workbench fits the available viewport

The system SHALL size the initial empty workbench against the available viewport rather than a fixed minimum canvas height. At common desktop viewport sizes, the header, role selector, empty workbench, and required bottom spacing SHALL not create an unnecessary page scrollbar.

#### Scenario: Recruiter opens the empty desktop page

- **WHEN** the page opens with no uploaded resumes and no selected candidate
- **THEN** the primary workbench is visible without an immediately appearing page scrollbar caused only by a fixed minimum height
- **AND** the role selector and upload action remain visible without clipping

### Requirement: Content overflow remains accessible

The system SHALL allow the page or an appropriate content region to scroll when evaluation results, evidence, notices, or form content exceed the available viewport. The viewport-fit behavior MUST NOT hide content or rely on permanently disabling document scrolling.

#### Scenario: Evidence content exceeds the viewport

- **WHEN** a candidate has enough evidence and findings to extend beyond the visible workbench
- **THEN** the recruiter can scroll to read all evidence and review controls
- **AND** no content is clipped by a global overflow rule

#### Scenario: Role editor contains a long rule text

- **WHEN** the recruiter opens the role editor and pastes a long multi-line rule
- **THEN** the editor remains usable with internal or page scrolling as needed
- **AND** the rest of the page is not forced into an unusable fixed-height state

### Requirement: Responsive behavior is preserved on small screens

The system SHALL preserve a natural vertical flow on mobile and narrow screens, including stacked workbench panels and scrollable role forms. Desktop viewport fitting MUST NOT reduce text, controls, or evidence below readable and operable sizes on smaller screens.

#### Scenario: Recruiter uses a narrow mobile viewport

- **WHEN** the page is opened on a narrow viewport
- **THEN** panels stack according to the existing responsive layout
- **AND** the page can scroll vertically to reach upload, results, evidence, and role management controls

