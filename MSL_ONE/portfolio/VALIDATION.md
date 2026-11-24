# Validation · 2026-11-14

## Automated checks

- Production React build passed.
- Lint passed with the existing hook-dependency warning in legacy `frontend/src/App.jsx:1293`.
- Node workspace tests: 27 passed, including navigation, three-column library, query examples, persistence, user questions, post-visit counts, real request wiring, honest failure states, separate escaped exports, source identity, human-review records, news refresh and layout-event isolation.
- Python tests: 22 passed (8 new CVRM API/source contracts plus the 14 existing workflow regression tests). Tests use synthetic fixtures and isolated SQLite storage.

Run `npm run build:cvrm`, `npm run test:cvrm`, `npm run build`, `npm run lint`, and `.venv/Scripts/python.exe -m unittest discover -s tests -v`.

On this Windows sandbox the backend tests required a writable TEMP/TMP directory (`../tmp/cvrm-tests`) and execution outside the sandbox because asyncio socketpair initialization stalled inside it. The unchanged full suite then passed.

## Live source checks

Public API search for `(Kim SG[Author] OR Kim SungGyun[Author]) AND finerenone` returned 3 PubMed records. Separate `finerenone` registry search returned 116 total, 12 displayed on the first page. These are observed counts on the verification date and may change.

The offline registry selection was subsequently checked directly against NCT02540993, NCT02545049, NCT05254002 and NCT02861534. They are a selected saved set, not a registry-wide result count. Actual responses and timestamps are retained in `live_search_check.json` and the trimmed browser bundle `verified-search.mjs`.

Google News RSS returned dated articles with publisher metadata. RSS summaries are stripped title/excerpt metadata; no full-article verification or generated scientific conclusion is claimed. Fixed dashboard cards have separate source-access descriptions and dates.

## Browser pass

In-app browser on `http://127.0.0.1:8000/cvrm`: left navigation, dashboard RSS cards, three-column library, real PubMed/registry request, basket selections, HCP author/news search and a manually entered question were verified. Post-visit practice capture and its count/percentage chart were checked. The follow-up potassium-monitoring search returned actual PubMed records, including PMID 34732509. Separate before/after report downloads completed and were saved to Downloads. Screenshots are saved alongside this file. Browser widths around 1265 and 933 pixels were visually checked; a full phone-device/printing pass was not performed.

The preview server was stopped after verification. Run `Start-CVRM.cmd` to use live searches again. Browser-local saved views and report files remain available offline.

Data remains browser-local. There is no shared account, background sync, automated KOL designation or public hosting. The old workflow and CV DOCX files were not modified by this extension.

## Human-review and company-context update

The human-review update introduced five checks covering regional/functional scope labels, required reviewer/source fields, before/after source snapshots, stage-specific report export, storage restoration, HTML escaping and preservation of earlier source snapshots. Production build passed; lint retains the same legacy warning. The backend was unchanged in this update, so the prior 22-test backend result remains applicable.

The browser pass confirmed the new review editor, before/after text, source and review-scope selectors, and the explicit practice-example label. `human-review-preview.png` records the form. No professional review or internal company approval is inferred from saving a user's review log.

## Compact Bayer-color workspace update

The final Node suite has 27 passing tests. Added checks cover an empty news field with placeholder, typed/default query submission, drawer dismissal, four visible news cards and metrics, stale-news loading behavior, news-only refresh requests, and separation of layout clicks from search pagination. The last check catches a browser-observed event collision that previously caused an unintended `/search` request with a nonnumeric page.

The standalone HTML was regenerated and the final React production build passed. Lint retains only the existing legacy hook warning. No backend code changed in this layout update.

At 1280×720 the dashboard document measured exactly 1280×720; four news cards shared a row, the checklist occupied the right column, and all four metrics ended above the footer. At 1024×768 the same major dashboard areas remained visible. Each of the five desktop tabs was visually checked. The library's three panels ended at the same viewport boundary and scroll internally. A 390×844 mobile pass confirmed 2×2 news cards and no horizontal overflow; mobile content scrolls vertically. Printing was not exercised.

The actual typed news query `바이엘 피네레논` returned 12 RSS records during verification. A blank-query refresh returned the documented Bayer/CV morning feed. The article drawer, Escape dismissal and focus return were checked. The final dashboard had no error toast, and a heading click no longer initiated a search.

Current screenshots: `dashboard-compact.png`, `library-compact.png`, `visit-compact.png`, `after-compact.png`, `report-compact.png` and `competencies-compact.png`. Earlier `*-preview.png` files document the preceding layout. See `DESIGN_NOTES.md` for palette and reference-video sources. The user-provided competency mapping is labelled as portfolio interpretation in its drawer.

## In-page document reports · 2026-11-15

Node suite: 31 passed. Four additional checks cover six-section report content and diagrams, search/report switching, persisted document tabs without duplication, honest unreviewed-source drafts, and mapping a live PubMed FIDELIO record to the completed case. Production React build passed. Lint retains only the existing legacy hook warning.

The HTML bundle and standalone case were regenerated. The report tab uses an embedded tabpanel rather than a drawer or separate report page; the six review details are collapsed initially. Backend behavior is unchanged.

Browser verification used a real `33264825[PMID]` search: PubMed returned one record and the parallel finerenone registry query returned 12 displayed / 116 total records. Creating the report from that PubMed record reused the FIDELIO tab. Population/design and the three HCP questions were expanded, including the design-flow diagram. Left/right arrow keys switched tabs and restored focus. At 1280×720 all six report headings and both visual summaries fit without page scrolling; the document measured 1280×720. At 390×844 no horizontal overflow occurred. Screenshots: `library-report-tabs.png` and `library-report-expanded.png`. The owned preview server was stopped after verification.

## News interactions and publisher summaries · 2026-11-15

Node tests: 34 passed. Backend tests: 30 passed, including seven new publisher-extraction tests and the new article-route contract. Production build passed; lint retains only the existing legacy hook warning. The existing Beautiful Soup dependency and Google News decoder 0.2.2 were installed in the project venv. Tests cover short metadata/body extracts, HTML stripping, blocked/non-article pages, caching, private addresses and redirect validation, inline seven-row expansion, and summary/source failure states.

The dashboard memo now appears below its card; browser geometry confirmed its top below the hovered card's bottom. “전체 7건 보기” expanded seven feed rows inline with no dialog and collapsed back to three. Clicking the actual supplied RSS article resolved to `https://www.monews.co.kr/news/articleView.html?idxno=415272`, displayed a short Korean publisher metadata extract, and retained a direct original-article link. It uses no LLM and is labelled as an automatic extract rather than a newly generated full-article analysis. Failed publisher access is separately labelled and retains the RSS source link. The API does not return the full article body.

Screenshots: `news-memo-below.png`, `news-original-summary.png`. The local server was restarted with the new endpoint and retained because the user is using the open local site. The HCP card explicitly states that official Bayer KOL designation is unconfirmed. Source-linked researcher and speaker details are in `FINERENONE_RESEARCHERS.md`.

## Original articles, closable reports and live CC · 2026-11-15

Final checks: Node 41 passed; Python 39 passed; production React build passed. Lint retains the existing legacy hook warning. All standalone HTML artifacts were regenerated.

The right drawer rendered the actual Medical Observer publisher page inside its iframe. Publisher framing restrictions retain a direct source link. Library and HCP preparation own independent closable report tabs; closing a report preserves basket documents. HCP reports stay on page three.

Browser QA confirmed separate manual question and practice CC, live keyword counts, missing-key connection UI, and preserved inputs. Automated recognition tests cover interim/final results and permission denial. No actual microphone session or paid OpenAI inference was run. Those require a supported browser, microphone permission and the visitor’s own API key/model access. Public hosting remains unverified. The local server was retained.

Evidence: news-original-frame.png, library-close-tabs.png, hcp-report-close.png, live-cc-keywords.png and question-api-connection.png. The CC screenshot is explicitly practice data.

## Pre-visit purpose, answer preparation and attachments · 2026-11-15

Node 43 passed; Python 42 passed; production build passed. HCP preparation now has a scientific purpose, three editable discussion examples, a separate answer-preparation question, editable PubMed/news queries, and three source columns. The browser retrieved four PubMed and four news records with the finerenone example. HCP identity and author research are optional collapsed panels. The completed review case has a direct button in preparation. Purpose and answer draft are included in the before-visit export.

Attachment extraction supports text PDF, DOCX and UTF-8 TXT/MD, maximum three files / 5MB each and 20,000 extracted characters per file. PDF extraction reads at most 30 pages; encrypted and image-only PDFs are unsupported. Raw files are not stored; extracted text is browser-local and sent to OpenAI only on the explicit LLM action. Automated checks cover text extraction, unsupported files and no LLM call during public search. Actual paid LLM inference and browser file chooser upload were not exercised. LLM output validates three anticipated questions and source IDs; PubMed abstracts and RSS excerpts remain clearly distinguished from a reviewed answer. Screenshot: previsit-answer-sources.png.

## Public portfolio and focused layouts · 2026-11-16 KST

Published publicly with Sites at https://msl-one-cvrm-portfolio.woodzheart.chatgpt.site. Project appgprj_6af874dec1bc8191a8b71c404168400d; saved version 3; commit 4f9882154af4b46a573457691cdf9be870d5b16c. Native deployment succeeded. An unauthenticated HTTP client received 200 and the public HTML. No local server is needed by visitors.

The public Worker provides PubMed, ClinicalTrials.gov, RSS news, preparation, optional OpenAI analysis and attachment extraction. Live public checks returned one FIDELIO paper and 12 trials; a Bayer finerenone query returned 11 news records. Google RSS occasionally rejected upstream requests, and failures remain visible rather than replaced with fabricated results. The public PDF endpoint extracted the synthetic test text successfully. Missing API connection blocks paid inference. No paid model call or microphone recording was tested. Public OpenAI session keys use a 1-hour encrypted HttpOnly/Secure/SameSite cookie, with the encryption key stored as a Sites secret. Visitor notes remain in browser-local storage and no local user records or API keys were copied into the deployed source.

HCP preparation separates question input from optional attachments. Speech CC, observations, source settings and detailed reports start collapsed. Post-visit recording and analysis actions occupy separate columns. Report summaries stay visible with detailed evidence in a two-column accordion grid. Browser QA checked the three layouts at 1280x720, and the report had no horizontal overflow at a 390px viewport. Screenshots: public-hcp-clean.png, public-after-clean.png, public-report-clean.png. Node frontend suite:45 passed; Worker suite:6 passed; frontend production build passed.
