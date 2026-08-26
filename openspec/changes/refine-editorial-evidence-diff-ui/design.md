## Context

`frontend/` already owns the recruiter workbench and its data flow: roles and batches are loaded through the existing API helpers, while `App.tsx` renders the queue, candidate list, evidence detail, and role editor. `styles.css` currently uses an archive-blue/teal document system. This change keeps that behavior and replaces the visual system with the approved C direction described by `proposal.md` and `specs/screening-workbench-editorial-ui/spec.md`.

## Goals / Non-Goals

**Goals:**

- Make the evidence relationship the primary visual hierarchy, not a dashboard summary.
- Give the queue, candidate result, and evidence detail stable visual regions that remain understandable during loading, empty, failed, and completed states.
- Encode the paper/editorial/CLI direction as reusable tokens and semantic component classes so later styling changes do not require scattered overrides.
- Preserve the current API calls, mutation behavior, result filters, role editor, and accessibility semantics while improving their presentation.
- Make the design testable through component states and a small set of deterministic visual review fixtures.

**Non-Goals:**

- No API, database, file-parser, evaluation-provider, or persistence changes.
- No new visual component framework, icon package, font package, or charting dependency.
- No OCR, ranking, bulk action, authentication, or recruiter workflow changes.
- No pixel-perfect dependency on the brainstorming companion HTML; the production tokens and states below are the source of truth.

## Decisions

### Use a tokenized paper/editorial system

Define the visual language in one `:root` token block and derive component rules from it:

| Token | Value | Use |
|---|---|---|
| `--paper` | `#F6F1E9` | App background and empty surfaces |
| `--paper-deep` | `#EEE9E1` | Queue/detail panels and selected rows |
| `--ink` | `#312D28` | Primary text and headings |
| `--muted` | `#877A6E` | Metadata and supporting copy |
| `--rule` | `#B9ADA0` | Hairline dividers and gutters |
| `--orange` | `#C65C30` | Active state, current marker, missing evidence |
| `--sage` | `#6E885E` | Satisfied evidence and completed status |

Noto Serif SC/Georgia remains reserved for titles and brief-like headings; IBM Plex Mono remains the utility face for scores, filenames, filters, state labels, and command-like copy. This keeps the Chinese reading experience humane while giving metadata the Claude Code-like terminal rhythm.

Alternative considered: retain the current archive-blue palette and only change spacing. Rejected because the user selected the paper-orange direction and the existing palette communicates an institutional archive rather than an editorial review tool.

### Split the workbench into explicit visual regions

Keep the current data ownership in `App.tsx`, but extract presentational regions where useful:

```text
WorkbenchShell
├── ReviewHeader       role / batch / threshold / status
├── QueuePanel         upload / files / explicit start action
├── CandidatePanel     filters / candidate rows / diff markers
└── EvidencePanel      score / findings / source excerpts / human-review note
```

The regions communicate through existing props and query state. No new state store is needed. Candidate rows stay buttons, the role manager stays an accessible dialog, and the evidence panel remains a readable document trail rather than a chart.

Alternative considered: rewrite the screen around a new table library or global navigation shell. Rejected because the workbench is a focused review flow, and adding a second state boundary would increase regression risk without improving the contract.

### Make evidence Diff a semantic display layer

Represent each finding with a small semantic marker and label:

- `+` / “满足条件” uses sage and identifies supported requirements.
- `-` / “待补证据” uses orange and identifies unmet or insufficient requirements.
- `>` / “当前审阅” identifies the selected candidate or source excerpt.
- A thin gutter and optional line number separate evidence metadata from quoted resume text.

The marker is rendered as text in the DOM, with color as a secondary cue. Existing `satisfied`, `unmet`, `evidence`, `score`, and `reason` data remain the only source of displayed findings.

Alternative considered: use icons only. Rejected because symbols are more legible in the chosen CLI language and maintain meaning when color is unavailable.

### Use desktop triage and mobile drill-down

At desktop widths, use a three-region grid with hairline vertical rules and an editorial top bar. At narrow widths, collapse to queue → candidates → evidence in document order; do not preserve three squeezed columns. Keep primary actions full-width and retain the same button labels.

Use `prefers-reduced-motion` to remove non-essential hover transitions. Keep focus outlines outside the paper surfaces so keyboard users can see focus against both warm and selected backgrounds.

Alternative considered: hide the queue or evidence panel at mobile widths. Rejected because explicit upload/start context and evidence review are core to the product's safety promise.

### Validate through behavior and visual checkpoints

Extend existing frontend tests for the semantic states (empty queue, ready file, processing, qualified, unqualified, failed) and keyboard-visible controls. Add a manual visual checklist at desktop and mobile widths covering the three-region hierarchy, paper tokens, Diff markers, and human-review label. Build and test commands remain the existing `npm run build` and `npm test`.

## Risks / Trade-offs

- [Warm paper and orange can reduce contrast] → Keep text in dark ink, test focus outlines and status labels, and verify contrast for every state instead of relying on the accent alone.
- [A denser CLI-like layout can feel opaque to recruiters] → Pair every symbol with plain Chinese labels and preserve the existing explanatory empty/error copy.
- [Extracting regions from the current monolithic component can cause state regressions] → Keep query/mutation ownership unchanged and move markup/styles incrementally with tests after each region.
- [Font loading may vary offline] → Define local system/serif/monospace fallbacks and ensure layout remains usable without remote font availability.

## Migration Plan

1. Introduce the token block and semantic region classes without changing API calls or query keys.
2. Restyle the header, queue, candidate rows, and evidence detail one region at a time; retain the current role dialog behavior.
3. Add/update frontend tests for the semantic markers, status labels, focus behavior, and responsive structure.
4. Run `npm run build` and `npm test`, then perform manual desktop/mobile review against the C direction.
5. Roll back by reverting the frontend-only change; no database or backend migration is required.
