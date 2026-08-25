## Context

This is a new application with no existing product modules. All server-side code lives beneath `backend/`; all web-client code lives beneath `frontend/`. See `proposal.md` for the motivation and the four capability specs for observable behavior. The system must accept personal resume data, apply user-authored role criteria through AgentScope, and make the resulting recommendation auditable instead of presenting a score as a black box.

## Goals / Non-Goals

**Goals:**

- Keep the first release a single FastAPI service plus a separate web client while retaining a clean boundary for batch work.
- Treat role profiles, individual requirements, prompts, and passing scores as user-managed data; a newly created profile begins at 80 but does not impose a global fixed cutoff.
- Return validated structured AI results with citations to extracted resume text and retain the exact criteria snapshot used for each batch.
- Give recruiters a fast, evidence-led workspace that is usable on desktop and smaller screens.

**Non-Goals:**

- OCR for scanned or image-only PDFs, candidate ranking across unrelated roles, automated rejection notices, and making final employment decisions.
- Parsing every resume layout perfectly, training a custom model, or building multi-tenant authentication and permissions in the first release.

## Decisions

### Product flow: upload is separate from evaluation

The workbench has three deliberate steps: add files, select an existing role profile, then activate **Start evaluation**. Uploading only creates a pending batch; it never calls the LLM. Once started, the service snapshots the profile and processes every ready file.

An evaluation batch has file-level states (`pending`, `ready`, `processing`, `completed`, `failed`, `unreadable`) and aggregate counts. The browser reads batch state only after a batch has been explicitly started, at a modest interval while work remains. This is status visibility for a user-triggered action, not automatic evaluation. It avoids holding a single browser request open through multiple document parses and LLM calls.

Alternative considered: a synchronous request that returns all results. It is acceptable for a single short resume but becomes fragile for a batch because gateway timeouts and a browser refresh can hide the outcome.

### Service architecture and persistence

`backend/` contains the FastAPI REST API for roles, requirements, pending uploads, batch creation, batch status, and candidate results. Its API layer delegates to four domain services: role-profile management, document ingestion, batch orchestration, and evaluation. Files are stored outside relational rows, while metadata, extracted text, criteria snapshots, job state, and results are stored in a relational database.

The evaluation runner is invoked after batch creation and writes each file's state independently, allowing valid resumes to complete even when another file cannot be read. The runner boundary must be replaceable by a durable worker queue before multi-process production deployment; a small initial deployment can use an in-process background runner. This keeps the first installation simple without making the API contract depend on its execution mechanism.

Alternative considered: run the AgentScope evaluation inside the upload handler. This couples upload success to LLM latency and makes partial failure handling unnecessarily difficult.

### Document handling

The ingestion service accepts only PDF and DOCX based on validated content and filename metadata, applies configurable size limits, stores an internal generated identifier rather than trusting the filename, and extracts text before a file is marked ready. PDF text extraction and DOCX parsing are separate adapters. A file with no usable text remains in the batch as `unreadable` with an actionable reason; it is never sent to the evaluator.

Alternative considered: claiming support for all PDFs through OCR. OCR adds operational cost and materially different accuracy expectations, so it is deferred.

### AgentScope evaluation contract

For each ready file, the orchestration service constructs an AgentScope task from the immutable profile snapshot and resume text. The task requests a schema-validated output: overall score (integer 0–100), per-requirement findings, qualified evidence snippets, unmet or insufficient requirements, a concise recommendation reason, and model-error details when applicable. The application—not model prose—determines qualified status by comparing the result score to the captured passing score.

The evaluation prompt must explicitly require evidence grounded in the supplied resume and prohibit using protected or sensitive personal characteristics. Invalid model output is retried according to a bounded policy; a persistent validation or provider failure becomes `failed`, never a fabricated score.

Alternative considered: ask the model to return only “qualified” or “unqualified.” A score plus structured findings is necessary for the required explanations and recruiter review.

### Versioned criteria and deletion behavior

Role profiles contain editable metadata, an evaluation prompt, a numeric passing score, and ordered requirements. Starting a batch creates a serialized criteria snapshot with a version identifier. Editing profile data affects only future batches. Profiles referenced by historical batches are soft-deleted or archived rather than physically removed, so result pages retain their original criteria.

Alternative considered: resolve current role data when opening historical results. That would silently rewrite the meaning of a past recommendation.

### Frontend stack and visual system

`frontend/` contains the React, TypeScript, and Vite client; it uses Tailwind CSS for the design tokens and layout, Radix primitives for accessible interactions, TanStack Query for API/cache state, and TanStack Table for result filtering. This is a focused operations interface, so server-rendering from Next.js adds little value, while a prebuilt administration component library would make the product look generic and make the evidence layout harder to own.

The planned top-level layout is:

```text
frontend/  # React client, UI tests, and static assets
backend/   # FastAPI application, AgentScope workflow, migrations, and API tests
openspec/  # Change planning artifacts
```

The concrete subject is an internal recruiter review desk; its audience is a recruiter comparing evidence rather than reading a dashboard. The page's single job is to make each automated recommendation easy to verify.

Design tokens:

| Token | Value | Use |
|---|---:|---|
| Ink | `#13212D` | Primary text and navigation |
| Archive blue | `#1E4D64` | Active controls and information hierarchy |
| Paper | `#F6F7F5` | Application background |
| File line | `#D9E1E4` | Dividers and document markers |
| Qualified teal | `#18796D` | Passing states and positive evidence |
| Review brick | `#B84E43` | Unqualified states and gaps |

Typography uses **Noto Serif SC** sparingly for role titles and assessment headings, **Noto Sans SC** for readable interface text, and **IBM Plex Mono** for scores, threshold comparisons, file metadata, and timestamps. The signature element is an expandable **evidence rail**: every score and reason has a slim colored connector to the resume excerpt that supports it. The rail turns “AI reasoning” into an inspectable document trail rather than decorative analytics.

Desktop layout:

```text
┌──────── Role title · threshold · rule version ──────────────┐
│ Files / upload    │ Candidate review list                    │
│ preparation state │ score · status · evidence rail          │
│ [Start evaluation]│ selected candidate detail / source proof │
└───────────────────┴─────────────────────────────────────────┘
```

On narrow screens, the upload queue, candidate list, and candidate detail become a single drill-down sequence. Keyboard focus is visible; status does not depend on color alone; reduced-motion preference removes progress animation. The design intentionally avoids the usual KPI-card hero and relies on the document/evidence relationship, which is specific to resume review.

## Risks / Trade-offs

- [LLM may hallucinate support for a requirement] → Require evidence snippets, validate output shape, show the criteria snapshot, and label the result as a recommendation requiring human review.
- [Personal data exposure through uploaded files or provider calls] → Restrict accepted file types and size, use access-controlled storage, minimize logs, define retention and deletion policies, and confirm the approved model-provider data policy before deployment.
- [Large batches may outlive an in-process worker] → Persist all state and isolate the runner behind a queue-compatible interface; use a durable worker before multi-instance deployment.
- [Text extraction is weak for scanned files or complex layouts] → Show `unreadable` rather than score empty text; introduce OCR only as a separately scoped enhancement.
- [User changes criteria while a batch is running] → Evaluate exclusively from the batch snapshot.

## Migration Plan

1. Deploy the database schema, private file storage configuration, and API with no existing-data migration required.
2. Deploy the frontend with role management and pending upload workflow before enabling the start-evaluation action.
3. Configure the LLM provider and run representative non-production resumes through structured-output validation.
4. Enable evaluation for a limited internal group; monitor parsing failures, model validation failures, and evaluation duration.
5. Roll back by disabling batch start and retaining uploaded files/results and role data for investigation; a new deployment can safely resume incomplete batches from persisted state.

## Open Questions

- Which approved LLM provider and data-retention arrangement will be used for resume content?
- What retention period and deletion workflow are required for uploaded resumes and extracted text?
