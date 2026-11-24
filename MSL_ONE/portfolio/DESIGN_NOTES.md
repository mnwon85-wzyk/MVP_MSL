# Compact workspace design · 2026-11-14

The desktop shell keeps primary navigation, page headings and major work areas in the initial viewport. Long source material scrolls within its panel; full reports, review forms and company context open in a side drawer. Existing evidence, browser state and export formats are retained.

## Dashboard

News occupies the main left panel; the morning checklist and HCP context occupy the right column. Four equally sized news cards form a single desktop row, with four summary metrics also kept on one row. Cards show short headlines and dates, with a hover/focus note and a separate article-reading drawer. The search field starts empty with a grey example; the search button and Enter submit the actual typed text to the existing RSS endpoint. A blank query uses the documented Bayer/CV morning query. Pending searches show skeletons and do not relabel old results as new ones.

The fixed-size news row supports simultaneous comparison. The overall news/checklist/HCP arrangement uses a bento grid with different panel sizes. A carousel would conceal topics the user asked to see together, so it is not used for these four cards.

## Components applied

- Short hero/title region with a single clear purpose on each page.
- Fixed sidebar and sticky header; desktop viewport shell.
- Responsive card, bento and split layouts.
- Accordion details for article/source content, questions, capture fields and report sections.
- Right-hand drawer for company context, HCP profile, review records, full reports, saved interactions and portfolio mapping.
- Dropdown source selection, hover/keyboard-focus notes, short toast feedback and skeleton loading.
- Restrained page/drawer transitions, button feedback and hover elevation. Reduced-motion settings disable these effects.
- No parallax or scroll-triggered hiding of primary content; the initial-viewport requirement takes priority.

At small widths the four topic cards become a 2×2 grid and content stacks vertically. Vertical scrolling is preserved for mobile readability. Desktop all-at-once visibility was verified at 1280×720 and 1024×768. A mobile 390×844 check covers reflow and horizontal overflow.

## Sources

Reference video: [코드깎는노인, 바이브코더가 반드시 알아야 할 필수 용어 24가지](https://www.youtube.com/watch?v=mlhKEy-2bgI), published 2026-10-25. The visible chapter list and available YouTube transcript were reviewed, including card layout at 2:14, bento grid at 2:35, drawer at 5:14 and interaction sections. These informed component selection rather than a copied page design.

Palette: [Bayer Identity Net distributor guide](https://idnet.bayer.com/sites/idnet/files/baag-idn-ags-003-24-co-branding-guide-distributor-241211-rz.pdf) documents Dark Blue #10384F, Bright Blue #00BCFF and Bright Green #89D329. The [official current brand page](https://www.bayer.com/en/about-us/explore-bayer/brand) describes the broader blue/green/purple palette. This independent portfolio uses dark blue for text and primary controls, bright blue and green for accents, and white surfaces for readable source material. It does not use the Bayer Cross or claim official affiliation.

The user-provided job-to-competency table appears as an explicitly labelled portfolio interpretation in the guide drawer. It is not treated as proof of work experience or a verified internal hiring rubric.

## Inline literature report tabs · 2026-11-15

The literature screen now keeps its own search/report tab strip. Each document offers “리뷰 리포트 생성”; adding a document to the basket also registers its report tab. Repeated creation reuses the same document identity, including the curated FIDELIO entry and PMID 33264825. Source snapshots and tabs persist in browser storage independently of the current search results.

The FIDELIO report uses a split visual summary above a two-column bento grid of six accordion sections: population/design, outcomes, safety, limitations, three discussion questions, and source/review scope. The initial view keeps every section heading visible; expanding a section scrolls inside the report panel. The visuals show the source-linked hazard ratio/confidence interval and separate event/discontinuation proportions on a common 0–25% bar scale. They do not imply a comparison between different outcome definitions. The study-design flow appears inside the population section. This applies the previously reviewed video’s tabs, card/bento and accordion patterns.

Other selected documents receive a clearly labelled source-based review draft. Unverified safety data, clinical conclusions and numerical diagrams are not invented. Registry reports remain distinguished from reviewed publications. Rendering a report needs no LLM connection.

## Original reading, closable tabs and conversation capture

News drawers now embed the original publisher website directly. They preserve the original link, use a sandboxed iframe, and respect X-Frame-Options/CSP restrictions. No publisher HTML is re-hosted to circumvent those restrictions. The actual Medical Observer article was visibly loaded in the right drawer during QA.

Report tabs have a separate close button at the right end, avoiding nested interactive buttons. The HCP page has its own reports and tabpanel, so author-paper report creation no longer redirects to literature search.

The capture screen uses a split layout: typed question plus CC on the left, live keyword frequencies plus optional LLM suggestions on the right. Incremental caption/chart DOM updates preserve typing. Domain-term frequencies are text counts rather than inferred clinical demand. Practice captions carry an explicit label. Speech-recognition results do not identify speakers. LLM analysis is user-triggered; including confirmed captions is a separate selection, and interim captions never enter the request. Session keys are handled by the backend, with validation and connection-required states kept distinct from an actual model response.

Implementation references: [MDN SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition), [MDN X-Frame-Options](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/X-Frame-Options), [OpenAI structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [OpenAI key management](https://developers.openai.com/api/docs/guides/api-keys).
