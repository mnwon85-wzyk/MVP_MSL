import gradio as gr

from services.fda import (
    search_fda_label,
    search_drugs_fda,
    fda_drugs_page,
)

from services.pubmed import (
    search_pubmed,
)

from services.clinicaltrials import (
    search_trials,
)


ASSETS = {
    "Jemperli (dostarlimab)": {
        "generic": "dostarlimab",
        "brand": "Jemperli",

        "pubmed_query": (
            '"dostarlimab" AND '
            '"endometrial cancer"'
        ),

        "trial_query":
            "dostarlimab",

        "gsk_sources": [
            {
                "title":
                    "GSK — RUBY Phase III overall survival results",
                "url":
                    "https://www.gsk.com/en-gb/media/press-releases/"
                    "positive-ruby-phase-iii-data-show-potential-for-"
                    "jemperli-dostarlimab-combinations-in-more-patients-"
                    "with-primary-advanced-or-recurrent-endometrial-cancer/",
            },
            {
                "title":
                    "GSK — European Commission expanded approval",
                "url":
                    "https://www.gsk.com/en-gb/media/press-releases/"
                    "european-commission-expands-jemperli-dostarlimab-"
                    "plus-chemotherapy-approval-to-all-adult-patients-"
                    "with-primary-advanced-or-recurrent-endometrial-cancer/",
            },
        ],
    },
}


def shorten(
    text,
    max_chars=1800,
):

    if not text:
        return (
            "No verified information "
            "returned by current source."
        )

    text = text.strip()

    if len(text) <= max_chars:
        return text

    return (
        text[:max_chars]
        + "..."
    )


def build_fda_card(
    label,
    application,
):

    if not label:

        return """
## FDA REGULATORY TRUTH / FDA 규제정보

⚠️ 현재 FDA Label API에서 일치하는
verified record를 찾지 못했습니다.
"""

    appl = (
        application.get(
            "application_number",
            "",
        )
        if application
        else label.get(
            "application_number",
            "",
        )
    )

    fda_url = (
        fda_drugs_page(appl)
    )

    return f"""
## FDA REGULATORY TRUTH / FDA 규제정보

### Indication / 적응증

{shorten(label.get("indications"))}

### Dosage & Administration / 용법·용량

{shorten(label.get("dosage"), 1000)}

### Regulatory identifiers / 규제 식별정보

**Application:** {appl or "N/A"}  
**Label effective time:** {label.get("effective_time") or "N/A"}

[Open FDA record / FDA 원문 열기]({fda_url})

🟢 **R1 — Regulatory**
"""


def build_safety_card(label):

    if not label:

        return """
## SAFETY / 안전성

현재 FDA label에서 verified safety record를
불러오지 못했습니다.
"""

    return f"""
## SAFETY / 안전성

### Warnings & Precautions / 경고 및 주의

{shorten(label.get("warnings"), 1800)}

### Adverse Reactions / 이상반응

{shorten(label.get("adverse_reactions"), 1800)}

### Boxed Warning / 박스경고

{shorten(label.get("boxed_warning"), 800)}

🟢 **Source: FDA prescribing information**
"""


def build_clinical_studies_card(
    label,
):

    if not label:

        return """
## PIVOTAL EVIDENCE / 주요 임상근거

FDA source unavailable.
"""

    clinical = label.get(
        "clinical_studies",
        "",
    )

    if not clinical:

        return """
## PIVOTAL EVIDENCE / 주요 임상근거

현재 FDA label API record에서
Clinical Studies section이 반환되지 않았습니다.

아래 Peer-reviewed Evidence에서 확인하세요.
"""

    return f"""
## PIVOTAL EVIDENCE / 주요 임상근거

### FDA Clinical Studies

{shorten(clinical, 3000)}

🟢 **Source: FDA Label — Clinical Studies**
"""


def build_pubmed(
    papers,
):

    lines = [
        "## PEER-REVIEWED EVIDENCE / 동료평가 논문",
        "",
        "| PMID | Title / 논문 | Year |",
        "|---|---|---|",
    ]

    for paper in papers[:10]:

        title = (
            paper.get(
                "title",
                "",
            )
            .replace("|", "\\|")
        )

        url = paper.get(
            "url",
            "",
        )

        lines.append(
            f"| {paper.get('id', '')} | "
            f"[{title}]({url}) | "
            f"{paper.get('date', '')} |"
        )

    if not papers:

        lines.append(
            "| - | No records retrieved | - |"
        )

    return "\n".join(lines)


def build_trials(
    trials,
):

    lines = [
        "## DEVELOPMENT LANDSCAPE / 개발 현황",
        "",
        "| NCT | Study / 연구 | Status | Phase |",
        "|---|---|---|---|",
    ]

    for trial in trials[:12]:

        title = (
            trial.get(
                "title",
                "",
            )
            .replace("|", "\\|")
        )

        lines.append(
            f"| {trial.get('id', '')} | "
            f"[{title}]({trial.get('url', '')}) | "
            f"{trial.get('status', '')} | "
            f"{trial.get('date', '')} |"
        )

    return "\n".join(lines)


def build_gsk_sources(
    asset_name,
):

    asset = ASSETS[
        asset_name
    ]

    lines = [
        "## GSK OFFICIAL / GSK 공식자료",
        "",
    ]

    for item in (
        asset["gsk_sources"]
    ):

        lines.append(
            f"- [{item['title']}]"
            f"({item['url']})"
        )

    return "\n".join(lines)


def build_summary(
    asset_name,
    label,
    papers,
    trials,
):

    asset = ASSETS[
        asset_name
    ]

    indication = (
        shorten(
            label.get(
                "indications",
                "",
            ),
            650,
        )
        if label
        else "No verified FDA label retrieved."
    )

    return f"""
# 60-SECOND ASSET REFRESH / 60초 자산 요약

### {asset_name}

**Generic / 성분명**  
{asset["generic"]}

### Approved Indication / 승인 적응증

{indication}

### Live Evidence / 실시간 근거

🔵 Peer-reviewed publications / 논문: **{len(papers)}**  
🟡 ClinicalTrials.gov studies / 등록 임상시험: **{len(trials)}**

### Evidence status

🟢 FDA Regulatory verified  
🔵 Peer-reviewed evidence  
🟡 Clinical development

**숫자나 적응증은 AI 기억값이 아니라
원문 source에서 확인된 정보만 사용합니다.**
"""


def refresh_asset(
    asset_name,
):

    asset = ASSETS[
        asset_name
    ]

    generic = asset[
        "generic"
    ]

    label = (
        search_fda_label(
            generic
        )
    )

    application = (
        search_drugs_fda(
            generic
        )
    )

    try:
        papers = (
            search_pubmed(
                asset[
                    "pubmed_query"
                ],
                limit=15,
            )
        )

    except Exception:
        papers = []

    try:
        trials = (
            search_trials(
                asset[
                    "trial_query"
                ],
                limit=15,
            )
        )

    except Exception:
        trials = []

    return (
        build_summary(
            asset_name,
            label,
            papers,
            trials,
        ),

        build_fda_card(
            label,
            application,
        ),

        build_clinical_studies_card(
            label
        ),

        build_safety_card(
            label
        ),

        build_pubmed(
            papers
        ),

        build_trials(
            trials
        ),

        build_gsk_sources(
            asset_name
        ),
    )


def render_asset():

    gr.Markdown(
        """
# MY ASSET / 내 자산

**Regulatory Truth → Clinical Evidence → Safety →
Development Landscape**

승인 정보, 임상 근거, 안전성, 개발 현황을
한 화면에서 빠르게 확인합니다.
"""
    )

    asset_selector = (
        gr.Dropdown(
            choices=list(
                ASSETS.keys()
            ),
            value=(
                "Jemperli (dostarlimab)"
            ),
            label=(
                "Select Oncology Asset / "
                "항암 자산 선택"
            ),
        )
    )

    refresh_button = (
        gr.Button(
            "REFRESH LIVE ASSET INTELLIGENCE / "
            "최신 자산 정보 불러오기",
            variant="primary",
        )
    )

    with gr.Row():

        with gr.Column(
            scale=3
        ):

            summary = (
                gr.Markdown(
                    """
아직 live refresh를 실행하지 않았습니다.
"""
                )
            )

        with gr.Column(
            scale=6
        ):

            fda = gr.Markdown()

    with gr.Row():

        clinical = (
            gr.Markdown()
        )

        safety = (
            gr.Markdown()
        )

    publications = (
        gr.Markdown()
    )

    development = (
        gr.Markdown()
    )

    gsk = (
        gr.Markdown()
    )

    refresh_button.click(
        fn=refresh_asset,
        inputs=[
            asset_selector
        ],
        outputs=[
            summary,
            fda,
            clinical,
            safety,
            publications,
            development,
            gsk,
        ],
    )