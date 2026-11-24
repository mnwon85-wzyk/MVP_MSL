# pages/search.py

import gradio as gr

from services.pubmed import search_pubmed
from services.clinicaltrials import search_trials

try:
    from services.fda import search_fda_label, normalize_label
except Exception:
    search_fda_label = None
    normalize_label = None


# ============================================================
# UTILITIES
# ============================================================

def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def md_escape(value):

    return (
        clean(value)
        .replace("|", "\\|")
        .replace("\n", " ")
    )


# ============================================================
# ICONS
# Lucide-style inline SVG
# ============================================================

ICON_BOOK = """
<svg viewBox="0 0 24 24"
     fill="none"
     stroke="currentColor"
     stroke-width="1.8"
     stroke-linecap="round"
     stroke-linejoin="round">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
    <path d="M4 4.5A2.5 2.5 0 0 1 6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5z"/>
</svg>
"""

ICON_FLASK = """
<svg viewBox="0 0 24 24"
     fill="none"
     stroke="currentColor"
     stroke-width="1.8"
     stroke-linecap="round"
     stroke-linejoin="round">
    <path d="M9 3h6"/>
    <path d="M10 9V3"/>
    <path d="M14 9V3"/>
    <path d="M8.5 9h7l4.5 9a2 2 0 0 1-1.8 3H5.8A2 2 0 0 1 4 18z"/>
</svg>
"""

ICON_SHIELD = """
<svg viewBox="0 0 24 24"
     fill="none"
     stroke="currentColor"
     stroke-width="1.8"
     stroke-linecap="round"
     stroke-linejoin="round">
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
    <path d="m9 12 2 2 4-4"/>
</svg>
"""

ICON_GLOBE = """
<svg viewBox="0 0 24 24"
     fill="none"
     stroke="currentColor"
     stroke-width="1.8"
     stroke-linecap="round"
     stroke-linejoin="round">
    <circle cx="12" cy="12" r="10"/>
    <path d="M2 12h20"/>
    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10"/>
    <path d="M12 2a15.3 15.3 0 0 0-4 10 15.3 15.3 0 0 0 4 10"/>
</svg>
"""


# ============================================================
# RESULT BUILDERS
# ============================================================

def build_pubmed(papers):

    if not papers:
        return "No PubMed publications were retrieved."

    output = []

    for i, paper in enumerate(papers, start=1):

        title = md_escape(paper.get("title"))
        url = clean(paper.get("url"))

        pmid = md_escape(paper.get("id"))
        journal = md_escape(paper.get("journal"))
        date = md_escape(paper.get("date"))

        abstract = clean(paper.get("abstract"))

        if len(abstract) > 1000:
            abstract = abstract[:1000] + "..."

        output.append(
            f"""
### {i}. [{title}]({url})

**PMID:** {pmid}  
**Journal:** {journal}  
**Date:** {date}

{abstract}

---
"""
        )

    return "\n".join(output)


def build_trials(trials):

    if not trials:
        return "No ClinicalTrials.gov records were retrieved."

    rows = [
        "| Study | Phase | Status |",
        "|---|---|---|",
    ]

    for trial in trials[:20]:

        title = md_escape(trial.get("title"))

        url = clean(trial.get("url"))

        phase = md_escape(trial.get("date"))

        status = md_escape(trial.get("status"))

        rows.append(
            f"| [{title}]({url}) | {phase} | {status} |"
        )

    return "\n".join(rows)


def build_fda(label):

    if not label:

        return (
            "No verified FDA label information "
            "was retrieved for this search."
        )

    indication = clean(
        label.get("indications")
    )

    dosage = clean(
        label.get("dosage")
    )

    if len(indication) > 1800:
        indication = indication[:1800] + "..."

    if len(dosage) > 1200:
        dosage = dosage[:1200] + "..."

    return f"""
### FDA Regulatory Information

**Brand:** {clean(label.get("brand_name"))}  
**Generic:** {clean(label.get("generic_name"))}

#### Approved indication

{indication or "Not retrieved"}

#### Dosage and administration

{dosage or "Not retrieved"}
"""


def build_safety(label):

    if not label:

        return (
            "No verified FDA safety information "
            "was retrieved for this search."
        )

    warnings = clean(
        label.get("warnings")
    )

    adverse = clean(
        label.get("adverse_reactions")
    )

    if len(warnings) > 1200:
        warnings = warnings[:1200] + "..."

    if len(adverse) > 1200:
        adverse = adverse[:1200] + "..."

    return f"""
### Safety

#### Warnings

{warnings or "Not retrieved"}

#### Adverse reactions

{adverse or "Not retrieved"}
"""


# ============================================================
# SEARCH
# ============================================================

def run_search(query, sources):

    query = clean(query)

    if not query:

        return (
            "Enter a search term.",
            "No literature results.",
            "No regulatory results.",
            "No development results.",
            "No safety results.",
            "0",
            "-",
        )

    sources = sources or []

    papers = []
    trials = []
    label = None

    errors = []

    # PubMed
    if "PubMed" in sources:

        try:

            papers = search_pubmed(
                query,
                max_results=15,
            )

        except Exception as exc:

            errors.append(
                f"PubMed: {exc}"
            )

    # ClinicalTrials.gov
    if "ClinicalTrials.gov" in sources:

        try:

            trials = search_trials(
                query,
                page_size=15,
            )

        except Exception as exc:

            errors.append(
                f"ClinicalTrials.gov: {exc}"
            )

    # FDA
    if "FDA" in sources:

        if search_fda_label and normalize_label:

            try:

                results = search_fda_label(query)

                if results:
                    label = normalize_label(
                        results[0]
                    )

            except Exception as exc:

                errors.append(
                    f"FDA: {exc}"
                )

        else:

            errors.append(
                "FDA service unavailable."
            )

    # EMA intentionally not shown as retrieved yet
    if "EMA" in sources:

        errors.append(
            "EMA live retrieval is not connected yet."
        )

    count = (
        len(papers)
        + len(trials)
        + (1 if label else 0)
    )

    status = "Live retrieval completed."

    if errors:

        status += "\n\n"

        status += "\n".join(
            f"- {error}"
            for error in errors
        )

    return (
        status,
        build_pubmed(papers),
        build_fda(label),
        build_trials(trials),
        build_safety(label),
        str(count),
        query,
    )


# ============================================================
# RESET
# ============================================================

def reset_search():

    return (
        "",
        [
            "PubMed",
            "ClinicalTrials.gov",
            "FDA",
            "EMA",
        ],
        "Ready.",
        "Run a search to view publications.",
        "Run a search to view regulatory information.",
        "Run a search to view development information.",
        "Run a search to view safety information.",
        "0",
        "-",
    )


# ============================================================
# PAGE
# ============================================================

def render_search():

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    gr.HTML(
        """
        <div class="page-header">

            <div class="page-title">
                1. SMART EVIDENCE SEARCH
            </div>

            <div class="page-subtitle">
                Find scientific evidence, regulatory updates
                and clinical development information —
                all in one place.
            </div>

        </div>
        """
    )

    # --------------------------------------------------------
    # TOP TWO COLUMNS
    # --------------------------------------------------------

    with gr.Row(
        equal_height=True,
    ):

        # ====================================================
        # LEFT
        # ====================================================

        with gr.Column(
            elem_classes=["search-card"],
        ):

            gr.HTML(
                f"""
                <div class="section-title">
                    Live retrieval from:
                </div>

                <div class="section-help">
                    Select trusted sources to search in real time
                </div>

                <div class="source-grid">

                    <div class="source-tile">

                        <div class="source-header">

                            <div class="source-icon">
                                {ICON_BOOK}
                            </div>

                            <div class="source-title">
                                PubMed
                            </div>

                        </div>

                        <div class="source-description">
                            Biomedical literature
                        </div>

                    </div>


                    <div class="source-tile">

                        <div class="source-header">

                            <div class="source-icon">
                                {ICON_FLASK}
                            </div>

                            <div class="source-title">
                                ClinicalTrials.gov
                            </div>

                        </div>

                        <div class="source-description">
                            Ongoing & completed trials
                        </div>

                    </div>


                    <div class="source-tile">

                        <div class="source-header">

                            <div class="source-icon">
                                {ICON_SHIELD}
                            </div>

                            <div class="source-title">
                                U.S. FDA
                            </div>

                        </div>

                        <div class="source-description">
                            Approval & safety information
                        </div>

                    </div>


                    <div class="source-tile">

                        <div class="source-header">

                            <div class="source-icon">
                                {ICON_GLOBE}
                            </div>

                            <div class="source-title">
                                EMA
                            </div>

                        </div>

                        <div class="source-description">
                            European regulatory information
                        </div>

                    </div>

                </div>
                """
            )

            sources = gr.CheckboxGroup(
                choices=[
                    "PubMed",
                    "ClinicalTrials.gov",
                    "FDA",
                    "EMA",
                ],
                value=[
                    "PubMed",
                    "ClinicalTrials.gov",
                    "FDA",
                    "EMA",
                ],
                show_label=False,
                elem_classes=["source-checkboxes"],
            )

        # ====================================================
        # RIGHT
        # ====================================================

        with gr.Column(
            elem_classes=["search-card"],
        ):

            gr.HTML(
                """
                <div class="section-title">
                    Enter your search query
                </div>

                <div class="section-help">
                    Use a disease, drug, indication,
                    biomarker or key scientific topic
                </div>
                """
            )

            query = gr.Textbox(
                show_label=False,
                lines=3,
                placeholder=(
                    "e.g. afatinib NSCLC, "
                    "dostarlimab endometrial cancer"
                ),
                elem_classes=["query-box"],
            )

            gr.HTML(
                """
                <div class="example-text">
                    Examples:
                    trastuzumab gastric cancer ·
                    CAR-T lymphoma ·
                    EGFR TKI resistance
                </div>
                """
            )

            with gr.Row():

                search_button = gr.Button(
                    "Search",
                    elem_id="search-button",
                )

                reset_button = gr.Button(
                    "Reset",
                    elem_id="reset-button",
                )

    # --------------------------------------------------------
    # RESULTS TITLE
    # --------------------------------------------------------

    gr.HTML(
        """
        <div class="result-divider"></div>

        <div class="result-heading">
            Search Results
        </div>

        <div class="result-help">
            Results stay collapsed until you choose
            which evidence section to review.
        </div>
        """
    )

    # --------------------------------------------------------
    # COUNTERS
    # --------------------------------------------------------

    with gr.Row():

        retrieved = gr.Textbox(
            label="Retrieved results",
            value="0",
            interactive=False,
            elem_classes=["metric-input"],
        )

        last_search = gr.Textbox(
            label="Last searched",
            value="-",
            interactive=False,
            elem_classes=["metric-input"],
        )

    # --------------------------------------------------------
    # RESULT TWO COLUMNS
    # --------------------------------------------------------

    with gr.Row():

        # ====================================================
        # LEFT RESULT
        # ====================================================

        with gr.Column():

            with gr.Accordion(
                "Literature Search · PubMed",
                open=False,
            ):

                literature = gr.Markdown(
                    "Run a search to view publications."
                )

        # ====================================================
        # RIGHT RESULT
        # ====================================================

        with gr.Column():

            with gr.Accordion(
                "Regulatory & Clinical Information",
                open=False,
                elem_classes=[
                    "regulatory-accordion"
                ],
            ):

                with gr.Accordion(
                    "FDA / EMA Approval Information",
                    open=False,
                ):

                    regulatory = gr.Markdown(
                        "Run a search to view regulatory information."
                    )

                with gr.Accordion(
                    "Clinical Evidence & Development",
                    open=False,
                ):

                    development = gr.Markdown(
                        "Run a search to view development information."
                    )

                with gr.Accordion(
                    "Safety",
                    open=False,
                ):

                    safety = gr.Markdown(
                        "Run a search to view safety information."
                    )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    status = gr.Markdown(
        "Ready."
    )

    # --------------------------------------------------------
    # TIPS
    # --------------------------------------------------------

    gr.HTML(
        """
        <div class="tips-card">

            <span class="tips-title">
                Tips for better results
            </span>

            <span class="tips-signature">
                <br>
                
            </span>

            <br><br>

            • Use drug + indication + biomarker where possible.<br>
            • Combine multiple scientific concepts for a more focused search.<br>
            • Confirm source traceability before external scientific use.

        </div>
        """
    )

    # --------------------------------------------------------
    # EVENTS
    # --------------------------------------------------------

    search_button.click(
        fn=run_search,
        inputs=[
            query,
            sources,
        ],
        outputs=[
            status,
            literature,
            regulatory,
            development,
            safety,
            retrieved,
            last_search,
        ],
    )

    reset_button.click(
        fn=reset_search,
        outputs=[
            query,
            sources,
            status,
            literature,
            regulatory,
            development,
            safety,
            retrieved,
            last_search,
        ],
    )