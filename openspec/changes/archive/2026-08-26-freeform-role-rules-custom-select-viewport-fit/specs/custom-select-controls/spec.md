## Purpose

为岗位选择和要求优先级提供统一、可访问且符合纸本橙视觉的下拉交互，避免浏览器原生菜单在不同平台上产生突兀且不可控的样式。

## ADDED Requirements

### Requirement: Select controls share a rounded visual language

The system SHALL render the role selector and requirement-priority selector with consistent rounded geometry, readable labels, clear placeholder and selected states, and visible focus styling. The closed controls SHALL visually match the surrounding editorial interface.

#### Scenario: No role has been selected

- **WHEN** the workbench has no active role
- **THEN** the role selector displays a readable placeholder and an affordance indicating that it can be opened
- **AND** the control does not look disabled or visually broken

#### Scenario: A role or priority is selected

- **WHEN** the recruiter chooses a role or a priority
- **THEN** the selected label is displayed without truncating its meaning
- **AND** the control uses the same border, radius, spacing, and focus treatment as the other custom select controls

### Requirement: Dropdown menus are usable and keyboard accessible

The system SHALL open a styled option list for each custom select, provide a visibly distinct highlighted and selected option, and support keyboard navigation, Enter selection, Escape dismissal, and dismissal when focus or pointer interaction moves outside the menu. The control SHALL expose appropriate combobox/listbox semantics to assistive technology.

#### Scenario: Recruiter opens a selector

- **WHEN** the recruiter clicks or focuses the role or priority selector
- **THEN** a rounded option surface opens adjacent to the control
- **AND** the available options remain readable and do not rely on the browser's native menu styling

#### Scenario: Recruiter selects with the keyboard

- **WHEN** the selector is focused and the recruiter presses ArrowDown or ArrowUp followed by Enter
- **THEN** the highlighted option becomes selected and the menu closes
- **AND** the selected value is reflected in the role form or workbench immediately

### Requirement: Select dismissal does not corrupt surrounding forms

The system SHALL close an open menu when the recruiter presses Escape or clicks outside it without changing the value unless an option was explicitly selected. Opening or closing a selector SHALL not submit the role form or trigger an evaluation.

#### Scenario: Recruiter abandons an open menu

- **WHEN** the recruiter clicks elsewhere or presses Escape while a menu is open
- **THEN** the menu closes
- **AND** the previously selected value remains unchanged

