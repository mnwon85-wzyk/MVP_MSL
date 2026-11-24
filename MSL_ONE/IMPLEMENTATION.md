# Inspection and implementation record

Source: `C:/Users/mnwon/OneDrive/Desktop/py/MSL_ONE.zip`, extracted into this project directory. The original ZIP remains unchanged.

## Existing implementation inspected

The ZIP contains a React 19 / Vite frontend, a FastAPI application in `api.py`, older Gradio pages (`app.py`, `pages/`), an alternate `backend/main.py`, source adapters in `services/`, public-signal classification in `intelligence/`, a legacy HCP JSON file, an unused SQLAlchemy model sketch, generated reports, and packaged Node dependencies/build outputs.

The active original frontend was a 95 KB `App.jsx` with Home, Smart Search, Treatment Landscape, Listen, Evidence Analysis, and Insight Analysis. State lived in React hooks; closing the browser lost searches, baskets and analyses. KR/EN covered only part of the old interface. HCP observations alone persisted through `database/hcp_insights.json`. No active database connection or session persistence existed.

Original endpoints retained: `GET /`, `POST /dashboard`, `POST /search`, `POST /landscape`, `POST /listen`, `GET|POST /hcp-insights`, `DELETE /hcp-insights/{id}`, `POST /analyze`, `POST /reports/export/pdf`, `POST /reports/export/pptx`.

Source integrations: PubMed E-utilities, ClinicalTrials.gov API v2, openFDA / Drugs@FDA, EMA medicines JSON, public Reddit RSS. Existing query expansion discovers asset aliases. Existing landscape begins with trial intervention discovery and then checks regulatory records. Legacy regulatory helpers suppress some errors; those helpers were not used for the new verified treatment retrieval. The new workflow reuses source adapters, normalizers and disease matching while retrieving regulatory context directly.

Gemini/OpenAI are routed through `services/llm_router.py`; credentials are server-side environment variables. PDF uses ReportLab and PPTX uses python-pptx in `services/dashboard.py`. The root requirements omitted FastAPI, uvicorn and both export libraries; these were added.

## New workflow and file scope

- Dashboard: SQLite tasks/note, therapeutic context, source snapshots and source-date-aware morning changes, open-question status/notes and Prepare hand-off.
- Prepare: one search/session, actual returned-record counts, source-separated evidence, verified FDA/EMA regulatory context, lazy cached public signals, rule-derived review needs plus optional source-referenced Gemini gap analysis, basket, English/Korean source-compiled briefs, optional evidence/public-signal analysis, old/new retrieval comparison, recent sessions, revision inspection and PDF/PPTX / AI package exports.
- Capture: synthetic observation, linked session/revision and selected evidence, deterministic field structure, optional Gemini interpretation, persistent questions/follow-up actions, saved interaction history, and access to legacy HCP observations.

New files: `workflow_store.py`, `workflow_sources.py`, `workflow_api.py`; `frontend/src/workflow/{WorkflowApp,DashboardPage,PreparePage,CapturePage,ReportPanel,components}.jsx`, `api.js`, `workflow.css`; `tests/test_workflow.py`, `README.md`, this record.

Changed files: `api.py` (router registration, version, export header exposure); `frontend/src/main.jsx` (new shell entry); `frontend/index.html` (title); root `package.json` (run/build/lint forwarding); `requirements.txt`; `.gitignore`; `services/clinicaltrials.py` (genuine update date); `services/fda.py` (ANDA URL prefix ordering fix); `services/dashboard.py` (scoped workflow report sections while preserving legacy export behavior).

The original React application/styles, Gradio pages, alternate backend, existing JSON, existing exports and original service endpoints remain present. The old React application is not the current entry point. Its one inherited lint warning remains; the new workflow files lint without warnings.

## SQLite and workflow APIs

SQLite tables: `sessions`, `session_versions`, `interactions`, `questions`, `tasks`, `settings`. Session payloads retain source metadata/text, search timestamps/status/queries, selected source keys, generated outputs and related-context snapshots. Parent IDs connect refreshed search versions. Every saved session mutation creates a recoverable revision; optimistic concurrency returns 409 for stale writes. Foreign keys retain entity relationships. Connections explicitly close on Windows.

New `/workflow` routes: `/state`, `/note`, `/context`, `/tasks[/{id}]`, `/prepares`, `/prepares/{id}`, `/prepares/{id}/versions`, `/prepares/{id}/signals`, `/brief`, `/analysis`, `/gaps`, `/signal-analysis`, `/package`, `/interactions`, `/interactions/{id}/analyze`, `/questions`, `/questions/{id}`, `/intelligence/refresh`. See FastAPI `/docs` for methods and typed request schemas.

## Validation and practical limitations

- Production frontend build passed; lint has only the inherited inactive-App warning.
- Ten offline backend tests pass: fresh-process restoration, version/concurrency behavior, closed loop, notes/tasks, cached signals, AI failure, invalid AI source rejection, regulatory separation, real source-date filtering, FDA links, historical question snapshots and PDF/PPTX generation.
- Live read-only requests returned real records from all four scientific integrations. The browser saved 76 returned evidence records and 26 verified regulatory records in the tested bounded NSCLC scenario. These are observed run counts, never product constants.
- Browser verification covered EN/KR labels with unchanged publication titles, evidence selection, saved-session restoration after restart/reload, English/Korean briefs, linked synthetic Capture, open-question creation, Dashboard follow-up prefill, saved tasks/notes and PDF generation.
- The supplied `.env` has no configured `GEMINI_API_KEY`. Live Gemini failure was handled without losing the captured observation, evidence or structured review. AI success was contract-tested with synthetic responses; live successful Gemini output could not be verified without a key.
- Public signal availability depends on Reddit RSS. The workflow caches successes/no-results and retains a retry state for unavailable sources. Public signals are never promoted to representative evidence.
- Regulatory context is bounded disease-level retrieval. Approved application/EMA status does not establish biomarker/setting eligibility or current clinical suitability. Full original indication text and source links remain available for review. Morning record changes do not establish scientific significance or question resolution.


## PREPARE basket update (2026-10-06)
- Evidence, treatment, public signals, and derived gaps can be selected into one persisted basket. Scientific evidence remains distinct from public signals and derived interpretations.
- Basket analysis is the default output and uses only the selected records, with context and limitations. Results save the input record snapshot and revision.
- PDF/PPTX exports use the saved analysis and its input snapshot, even after basket selections change. HCP source-compilation briefs remain a separate output.
- Existing sessions and historical revisions remain readable; selections use optimistic revision checks. New gap generation clears obsolete gap selection only.
- Validation: 12 offline contract tests, including mixed-category selection, invalid references, analysis input scope, immutable output snapshot, and PDF/PPTX exports. Frontend production build passes; existing legacy App.jsx hook lint warning remains.


## Gemini settings and GSK Oncology sample
- The header opens a password-input dialog to set the Gemini API key and test the backend connection. The key stays in backend process memory, is never echoed by the API, and is not persisted to SQLite/browser storage. Restarting the backend requires re-entry. Requests to credential mutation/testing endpoints are restricted to local clients and local origins; provider errors are sanitized.
- PREPARE can create a fictional Keytruda-using gynecologic HCP visit for GSK Jemperli vs MSD/Merck Keytruda, using PubMed records 36972026/36972022/40616865/40044930, RUBY NCT03981796, NRG-GY018 NCT03914612, and dated FDA approval announcements. External source failures are displayed; scientific records are not synthesized.
- The starting basket selects retrieved papers/registries, the two regulatory summaries, and a comparability review need. The generated brief is explicitly source compilation, not Gemini analysis. AI results remain empty until a real analysis runs.
- Added optional comma-separated drug search terms to scientific/regulatory retrieval. For drug searches, free-text meeting setting stays in analysis context instead of restricting retrieval verbatim. Biomarker/setting applicability still requires review.
- 14 contract tests pass; production build passes. Legacy App.jsx retains its existing hook lint warning.
