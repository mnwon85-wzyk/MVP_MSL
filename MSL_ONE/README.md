# MSL ONE

Independent portfolio MVP for a closed-loop Field Medical scientific workflow. Use synthetic HCP interactions only. No patient-identifiable or confidential company data. This is not medical advice or a validated clinical decision-support platform.

## Run locally

Open two terminals in this directory (`MSL_ONE`, the extracted project root).

Backend, using Python 3.12 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api:app --reload --port 8000
```

Frontend:

```powershell
npm --prefix frontend install
npm run dev
```

Open http://localhost:5173. `npm run dev` also works directly inside `frontend`.
The backend is **api:app**. The legacy `backend/main.py` and Gradio `app.py` are preserved but are not this React application's entry point.

Create `.venv` and install the dependencies before running the FastAPI application. If Python is not on PATH, use `.\.venv\Scripts\python.exe -m uvicorn api:app --reload --port 8000`.

API keys belong only in the backend environment / root `.env`. Do not copy `.env` into `frontend`, prefix a secret with `VITE_`, or commit secrets. Existing provider routing remains server-side. Optional `VITE_API_BASE` configures only the backend URL.

## Workflow

### Bayer CVRM portfolio extension (2026-11-14)

The initial React screen opens a CVRM workspace with five left navigation items: 오늘의 브리핑, 논문·임상 검색, HCP 방문 준비, 대화·후속 근거, 방문 리포트. Existing Dashboard, Live Search / Prepare, Capture, backend endpoints and SQLite workflow remain available through “기존 워크스페이스”. This is an independent portfolio, not a Bayer tool or endorsed product.

For actual in-page searches, run `Start-CVRM.cmd` and open http://127.0.0.1:8000/cvrm. The existing `.venv` runs `api:app`; no AI key is needed for PubMed, ClinicalTrials.gov or Google News RSS retrieval. Run from a terminal with `.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000` if preferred. Restart the backend after Python changes. The API listens only on localhost.

Open `portfolio/MSL_ONE_CVRM_MVP.html` directly for offline browsing, notes, charts and exports. Direct-file mode explains how to start the local API when a live search is requested; it does not bypass browser origin restrictions. Actual saved author-paper and pivotal trial records are bundled with source IDs and retrieval timestamps. New searches and saved records are displayed separately. Search failures never substitute saved evidence as new results.

Dashboard news cards show a note on hover or keyboard focus; it disappears when focus/pointer leaves. RSS metadata is labelled as title/excerpt only. Automatic news refresh runs when the saved feed is older than 30 minutes; manual refresh is available. Source website content is not automatically fact-checked.

News memos appear below their cards. “전체 보기” expands the feed inline. A live article opens its original publisher page in the right drawer after resolving the Google News URL. Publisher framing restrictions are respected and show a direct original-article link instead. This needs the local server and internet, but no LLM key. `services/news_article.py` bounds resolution requests, rejects private destinations, caches metadata, and returns no full article body; the iframe loads directly from the publisher.

Literature and HCP-preparation pages keep separate report-tab collections. Each tab has its own × button; closing a report leaves the selected source document in the basket. HCP reports stay on the HCP-preparation page.

Post-visit capture separates the typed question from continuous Korean CC captions using the browser SpeechRecognition API. Interim/final captions update the local domain-keyword chart without replacing the question field. Final text is browser-local; no audio files are saved by this app. Browser recognition services may process audio remotely. Actual microphone use depends on browser support, permissions and network access; a clearly labelled practice-caption button is provided for demonstrations.

“질문 분석 · LLM” optionally includes confirmed captions and uses a per-browser OpenAI connection, never the interim captions. The server retrieves up to three PubMed records and validates three generated discussion questions against their source IDs. API keys stay in server memory behind an HttpOnly session cookie, with one-hour connection validity; they are not put in the HTML bundle, browser storage or database. The local keyword chart needs no LLM. Actual paid LLM requests require the visitor's valid API key and model access. Public hosting, rate/cost controls and real multi-user operation have not been verified.

The compact Bayer-color dashboard places news on the left and the morning checklist on the right. Four news cards and four summary metrics each share one desktop row. News search starts empty with a grey example; Enter and the button submit the entered query. Desktop major work areas fit at 1280×720 and 1024×768; long material scrolls inside panels or opens in drawers. Mobile uses two-column news cards and vertical scrolling. The portfolio guide drawer maps the user-provided job requirements to demonstrable tasks. Design sources and interaction choices are documented in `portfolio/DESIGN_NOTES.md`.

The library has paper, registry and basket columns; documents start collapsed. Query examples are editable. HCP preparation uses real public article/publication examples, name/hospital/department/product fields and an editable PubMed author query. Names require affiliation checks; neither authorship nor an event appearance establishes Bayer KOL designation. Pre-visit questions are user-authored. Post-visit input separates question, observation, interpretation, hypothesis, insight and follow-up. Editable search terms retrieve related source abstracts, registries and news; clinical interpretation remains a human review task. Conversation examples are fictional and are not attributed to the public HCP.

Before/after reports export separately or together. They include selected papers/registries, user questions, study-context/result cards, an E01 source-linked hazard-ratio illustration when selected, and recorded question-topic counts. Counts describe the saved set, not market demand or comparative drug efficacy. Ready-made examples are `portfolio/MSL_ONE_CVRM_Before_Visit.html`, `MSL_ONE_CVRM_After_Visit.html` and `MSL_ONE_CVRM_Report.html`. The public CVRM MVP is available at https://msl-one-cvrm-portfolio.woodzheart.chatgpt.site/. CVRM state uses the `msl-cvrm-v2` browser-local key, separate from the existing SQLite database; there is no cross-device sync or multi-user authentication.

Humanizer editorial guidance is vendored under `vendor/humanizer/` with its MIT license and source metadata. It was applied to the five new screens and report copy; no automatic alteration of scientific source text is performed.

See `portfolio/RECORDING_GUIDE.md`, `portfolio/captions.ko.srt`, `portfolio/captions.en.srt`, `portfolio/SOURCE_AUDIT.md` and `portfolio/VALIDATION.md` for the recording flow, captions, source access levels and test results. Here GCP means Good Clinical Practice; quality principles are borrowed without claiming clinical-trial validation or certification.

```powershell
npm run build:cvrm
npm run test:cvrm
```

The standalone HTML is generated from the same evidence, renderer and styles as the React page; rebuild after changing `frontend/src/cvrm/`.

1. Dashboard: add tasks and notes. Saved therapeutic context enables morning intelligence, automatically checked when older than six hours. Refresh explicitly for a newer snapshot.
2. Prepare: enter synthetic HCP, disease, optional biomarker/setting, and scientific question. The synthetic scenario button fills context only; it does not manufacture scientific results.
3. Search once. Evidence and verified regulatory context are saved together. Counts reflect the returned records saved in this bounded session, not total database hits. Signals load once on first view and are cached. Gaps initially express rule-derived review needs; they do not establish absence of evidence.
4. Select evidence. Generate a source-compiled HCP meeting brief without requiring AI. Optionally use Gemini for source-grounded analysis / internal intelligence. Export existing PDF/PPTX formats, or copy/download the provider-independent AI review package.
5. Capture the synthetic exchange, linked to the Prepare session/revision and selected evidence. Structure observations, optionally request AI interpretation, then add an unresolved scientific question or prepare a follow-up.
6. Dashboard shows open questions. Matching therapeutic context may link newly retrieved evidence to a question; relevance and resolution require human review.

KR/EN switches interface labels. Scientific source titles, abstracts, indications, quotations, and user-entered material stay in their original language. Briefs and analyses are generated separately by requested language.

## Persistence and provenance

`database/workflow.sqlite3` stores all meaningful workflow data. It uses SQLite WAL, foreign keys, atomic revisions, and optimistic concurrency checks. SQLite connections close after each operation. No separate database server is required.

- `sessions`: bounded evidence/treatment snapshots, source statuses/queries, cached signals, derived review needs, evidence selections, briefs/analyses, context, timestamps and parent session.
- `session_versions`: recoverable snapshots of every saved session revision. The revision selector opens history read-only.
- `interactions`: synthetic observations, linked session/revision and selected evidence, structured/AI interpretation.
- `questions`: linked interaction/session, scientific context, evidence gap, follow-up action/notes and status.
- `tasks`: daily tasks.
- `settings`: quick note, saved therapeutic context and latest intelligence snapshot.

Refresh creates a **new linked session**, leaving previous search context intact. New retrieval is distinct from a confirmed scientific change. Source record hashes identify changed retrieved text/status; they do not infer clinical significance. Partial intelligence failures retain previously retrieved records for affected sources.

FDA treatment records require an approved NDA/BLA application plus a disease indication match. EMA treatment records require authorised status plus a disease indication match. Original indication text is retained. Neither implies biomarker/setting eligibility without review. Trial discovery never establishes approval; trial records stay in Evidence. Search is bounded and not exhaustive.

Legacy HCP JSON and historical generated reports are preserved. Legacy source, analysis and export endpoints remain available. `database/models.py` was an unused earlier SQLAlchemy model sketch; the active workflow uses standard-library SQLite.

Close the backend before copying the database, or use SQLite's backup API to make a consistent backup. Keep the SQLite file private; it is local MVP storage with no multi-user authentication. Browser closure does not remove saved records. Explicitly save notes before immediately closing the browser.

## Verify

```powershell
npm run build
npm run lint
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests isolate workflow storage and use clearly synthetic contract fixtures, never product evidence. They cover persistence in a fresh interpreter, revisions/conflicts, the closed loop, AI failure, lazy signal caching, notes/tasks, regulatory separation, and existing report exports. Live source access depends on the network; failures remain visible and produce no substitute evidence.
