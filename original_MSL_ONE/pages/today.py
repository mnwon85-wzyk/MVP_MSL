import gradio as gr
import pandas as pd
import plotly.express as px

from services.pubmed import search_pubmed
from services.clinicaltrials import search_trials


ASSETS = {
    "Jemperli (dostarlimab)": {
        "query": (
            'dostarlimab AND '
            '(endometrial OR rectal OR colon)'
        ),
        "moa": "Anti-PD-1 antibody",
        "focus": (
            "Endometrial cancer; "
            "dMMR/MSI-H colorectal/rectal development"
        ),
        "status": "Approved + ongoing late-stage development",
    },

    "Blenrep (belantamab mafodotin)": {
        "query": (
            '"belantamab mafodotin" '
            "AND multiple myeloma"
        ),
        "moa": "Anti-BCMA antibody-drug conjugate",
        "focus": "Multiple myeloma",
        "status": "Approved / registration + ongoing development",
    },

    "Ojjaara / Omjjara (momelotinib)": {
        "query": (
            "momelotinib AND "
            "(myelofibrosis OR myelodysplastic)"
        ),
        "moa": "JAK1 / JAK2 / ACVR1 inhibitor",
        "focus": "Myelofibrosis; MDS development",
        "status": "Approved + Phase II development",
    },

    "Zejula (niraparib)": {
        "query": (
            "niraparib AND "
            "(ovarian OR glioblastoma)"
        ),
        "moa": "PARP inhibitor",
        "focus": "Ovarian cancer; glioblastoma development",
        "status": "Approved + late-stage development",
    },

    "Ris-Rez (risvutatug rezetecan)": {
        "query": (
            '"risvutatug rezetecan" '
            "OR GSK5764227"
        ),
        "moa": "B7-H3-targeted antibody-drug conjugate",
        "focus": (
            "SCLC and additional solid tumours"
        ),
        "status": "Late-stage development",
    },

    "Velzutatinib": {
        "query": (
            "velzutatinib OR "
            "GSK6042981 OR IDRX-42"
        ),
        "moa": "KIT inhibitor",
        "focus": "Gastrointestinal stromal tumours",
        "status": "Late-stage development",
    },

    "Jideytro": {
        "query": "Jideytro NSCLC",
        "moa": "GSK late-stage NSCLC medicine",
        "focus": "NSCLC",
        "status": "Added to GSK late-stage oncology portfolio in 2026",
    },

    "Neladalkib": {
        "query": "neladalkib NSCLC",
        "moa": "GSK late-stage NSCLC medicine",
        "focus": "NSCLC",
        "status": "Added to GSK late-stage oncology portfolio in 2026",
    },
}


def asset_summary(asset_name):

    asset = ASSETS[asset_name]

    return f"""
### 60-SECOND ASSET REFRESH

**Asset**  
{asset_name}

**Mechanism / Modality**  
{asset["moa"]}

**Current Focus**  
{asset["focus"]}

**Portfolio Status**  
{asset["status"]}

---

### LIVE SOURCE LAYERS

🔵 PubMed  
🟡 ClinicalTrials.gov

Click **Refresh Live Data** to retrieve current evidence.
"""


def build_chart(
    paper_count,
    trial_count,
):
    df = pd.DataFrame(
        {
            "Source": [
                "Peer-reviewed Evidence",
                "Clinical Trials",
            ],
            "Count": [
                paper_count,
                trial_count,
            ],
        }
    )

    fig = px.bar(
        df,
        x="Source",
        y="Count",
        text="Count",
        title="Live Medical Intelligence",
    )

    fig.update_traces(
        marker_color=[
            "#4B83C3",
            "#E3AD3E",
        ]
    )

    fig.update_layout(
        template="plotly_white",
        height=350,
        xaxis_title="",
        yaxis_title="Retrieved records",
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=30,
        ),
    )

    return fig


def refresh_live_asset(asset_name):

    asset = ASSETS[asset_name]

    query = asset["query"]

    paper_error = None
    trial_error = None

    try:
        papers = search_pubmed(
            query,
            limit=25,
        )
    except Exception as exc:
        papers = []
        paper_error = str(exc)

    try:
        trials = search_trials(
            query,
            limit=25,
        )
    except Exception as exc:
        trials = []
        trial_error = str(exc)

    rows = []

    for item in papers[:8]:
        rows.append(
            {
                "Source": "PubMed",
                "ID": item["id"],
                "Title": item["title"],
                "Status": "Published",
            }
        )

    for item in trials[:8]:
        rows.append(
            {
                "Source": "ClinicalTrials.gov",
                "ID": item["id"],
                "Title": item["title"],
                "Status": item["status"],
            }
        )

    table = pd.DataFrame(
        rows,
        columns=[
            "Source",
            "ID",
            "Title",
            "Status",
        ],
    )

    source_text = f"""
### SOURCE TRACE

**Search query**

`{query}`

🔵 PubMed retrieved: **{len(papers)}**  
🟡 ClinicalTrials.gov retrieved: **{len(trials)}**

"""

    if paper_error:
        source_text += (
            f"\n⚠️ PubMed error: {paper_error}"
        )

    if trial_error:
        source_text += (
            f"\n⚠️ ClinicalTrials.gov error: {trial_error}"
        )

    source_text += """

---

Results represent records returned by the current live search.

A low result count does **not** establish absence of evidence.
"""

    action = f"""
### TODAY'S SCIENTIFIC WORKFLOW

**Selected asset:** {asset_name}

**Live evidence retrieved**

- Peer-reviewed records: **{len(papers)}**
- Registered clinical trials: **{len(trials)}**

### Suggested next step

Review retrieved evidence → identify important changes →
run AI evidence synthesis in **SMART SEARCH** →
capture scientific questions requiring further exploration.
"""

    return (
        asset_summary(asset_name),
        len(papers),
        len(trials),
        build_chart(
            len(papers),
            len(trials),
        ),
        table,
        action,
        source_text,
    )


def change_asset(asset_name):
    return asset_summary(asset_name)


def render_today():

    gr.Markdown(
        """
# TODAY

### Live Oncology Medical Intelligence

Select a GSK Oncology asset and retrieve current
PubMed and ClinicalTrials.gov evidence.
"""
    )

    asset_selector = gr.Dropdown(
        choices=list(ASSETS.keys()),
        value="Jemperli (dostarlimab)",
        label="GSK Oncology Asset",
    )

    refresh_button = gr.Button(
        "Refresh Live Data",
        variant="primary",
    )

    with gr.Row():

        # LEFT
        with gr.Column(
            scale=2,
            min_width=280,
        ):

            with gr.Accordion(
                "MY ASSET",
                open=True,
            ):
                asset_box = gr.Markdown(
                    asset_summary(
                        "Jemperli (dostarlimab)"
                    )
                )

            with gr.Accordion(
                "WORKFLOW",
                open=False,
            ):
                gr.Markdown(
                    """
TODAY  
↓  
PREPARE  
↓  
ENGAGE  
↓  
LISTEN  
↓  
CONNECT  
↓  
SHARE
"""
                )

        # CENTER
        with gr.Column(
            scale=5,
            min_width=550,
        ):

            with gr.Row():

                paper_count = gr.Number(
                    value=0,
                    label="Live Publications",
                    interactive=False,
                )

                trial_count = gr.Number(
                    value=0,
                    label="Live Clinical Trials",
                    interactive=False,
                )

            chart = gr.Plot(
                value=build_chart(0, 0)
            )

            gr.Markdown(
                "### LATEST RETRIEVED RECORDS"
            )

            records = gr.Dataframe(
                headers=[
                    "Source",
                    "ID",
                    "Title",
                    "Status",
                ],
                interactive=False,
                wrap=True,
            )

        # RIGHT
        with gr.Column(
            scale=2,
            min_width=290,
        ):

            with gr.Accordion(
                "INSIGHT & ACTION",
                open=True,
            ):
                action_box = gr.Markdown(
                    """
Refresh live data to begin today's
scientific intelligence workflow.
"""
                )

            with gr.Accordion(
                "SOURCE TRACE",
                open=True,
            ):
                source_box = gr.Markdown(
                    """
No live search has been run yet.
"""
                )

            with gr.Accordion(
                "EVIDENCE GOVERNANCE",
                open=False,
            ):
                gr.Markdown(
                    """
🟢 Regulatory  
🟢 Guideline  
🔵 Peer-reviewed  
🔵 Congress  
🟡 Development  
🟣 Field Signal  
🟠 Patient Signal  
⚪ AI-derived

**AI synthesis is never treated as verified evidence.**
"""
                )

    asset_selector.change(
        fn=change_asset,
        inputs=asset_selector,
        outputs=asset_box,
    )

    refresh_button.click(
        fn=refresh_live_asset,
        inputs=asset_selector,
        outputs=[
            asset_box,
            paper_count,
            trial_count,
            chart,
            records,
            action_box,
            source_box,
        ],
    )