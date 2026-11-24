# MSL ONE — Medical Affairs Portfolio

Independent portfolio prototypes for reviewing clinical evidence, preparing scientific questions, and structuring follow-up work.

**[Open the published CVRM MVP](https://msl-one-cvrm-portfolio.woodzheart.chatgpt.site/)** · No login is required to view the portfolio or completed review case. Optional LLM features require the visitor's own API key.

## Projects

| Folder | Contents |
| --- | --- |
| [MSL_ONE](MSL_ONE/) | Current integrated application: the CVRM portfolio MVP and the preserved original Medical Affairs workspace. |
| [original_MSL_ONE](original_MSL_ONE/) | Earlier MSL ONE source snapshot, preserved separately for reference. |
| [Public deployment source](MSL_ONE/sites/msl-one-portfolio/) | Cloudflare Worker source, public page, build script and tests used for the published MVP. |
| [Standalone MVP](MSL_ONE/portfolio/MSL_ONE_CVRM_MVP.html) | Download and open for offline browsing. Live searches require the local API or published site. |
| [Completed review case](MSL_ONE/portfolio/MSL_ONE_CVRM_Review_Case.html) | Finerenone FIDELIO-DKD: population/design, efficacy, safety, limitations, HCP discussion questions and sources. |

## Current MVP

- Morning briefing with source-linked Bayer/CV news.
- PubMed and ClinicalTrials.gov search, document basket and closable review tabs.
- HCP visit preparation, previous-visit follow-up, editable scientific objectives and questions, and optional file attachments.
- Separate post-visit observations, interpretations, hypotheses and follow-up actions; optional browser speech captions and keyword charts.
- Before/after visit reports and HTML export.

This is a portfolio prototype, not a Bayer product, a clinical decision-support system, or evidence of actual MSL/HCP engagements. HCP/publication examples do not establish official Bayer KOL status. Source content and AI drafts require human review. News feeds can reject or rate-limit requests. Microphone support depends on the browser and permission; no paid LLM or actual microphone validation is claimed.

## Run the current application

Use Python 3.12+ and a current Node.js LTS release.

```powershell
cd MSL_ONE
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/cvrm. The checked-in standalone HTML is served by FastAPI. To rebuild it after editing the CVRM source, run `node scripts/build-cvrm.mjs` from `MSL_ONE`.

For the React interface, run `npm ci --prefix frontend` and `npm --prefix frontend run dev` in a second terminal; then open the URL Vite prints. The original integrated workspace remains accessible through the React application's legacy-workspace control.

## Tests and public build

- Current UI: `cd MSL_ONE`, then `node scripts/test-cvrm.mjs`.
- Python backend: install the requirements, then `python -m unittest discover -s tests -v` from `MSL_ONE`.
- Public Worker: `npm ci`, `npm test`, and `npm run build` from `MSL_ONE/sites/msl-one-portfolio`. See that folder's README for the optional runtime secret and publishing setup.

## Files intentionally omitted

API keys, real `.env` files, local HCP interaction JSON, SQLite databases, generated user reports, virtual environments, `node_modules`, nested Git repositories, Sites account bindings, deployment archives and build output are not included. Use the example environment file for local setup. Do not commit patient information or confidential company material.

Third-party humanizer editorial guidance retains its own MIT license in [vendor/humanizer](MSL_ONE/vendor/humanizer/). No license is added to the project's own code by this upload.
