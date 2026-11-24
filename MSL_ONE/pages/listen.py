import gradio as gr
import pandas as pd
import plotly.express as px

from services.community import (
    search_patient_voice,
    reddit_available,
    naver_available,
)

from intelligence.patient_voice import (
    analyze_patient_voice,
)


def escape_md(text):

    if text is None:
        return ""

    return (
        str(text)
        .replace("|", "\\|")
        .replace("\n", " ")
    )


def build_source_results(records):

    if not records:

        return """
### 검색 결과 없음 / No results

현재 검색 조건에서 공개 Patient Voice signal을 찾지 못했습니다.
"""

    rows = [
        "| Source | Community | Theme | Title / 제목 |",
        "|---|---|---|---|",
    ]

    for item in records[:60]:

        source = escape_md(
            item.get(
                "source",
                "",
            )
        )

        community = escape_md(
            item.get(
                "community",
                "",
            )
        )

        theme = escape_md(
            item.get(
                "theme",
                "",
            )
        )

        title = escape_md(
            item.get(
                "title",
                "",
            )
        )

        url = item.get(
            "url",
            "",
        )

        linked_title = (
            f"[{title}]({url})"
            if url
            else title
        )

        rows.append(
            f"| {source} | "
            f"{community} | "
            f"{theme} | "
            f"{linked_title} |"
        )

    return "\n".join(rows)


def build_theme_chart(summary):

    if not summary:

        df = pd.DataFrame(
            {
                "Theme / 주제": [],
                "Count / 건수": [],
            }
        )

    else:

        df = pd.DataFrame(summary)

    fig = px.bar(
        df,
        x="Count / 건수",
        y="Theme / 주제",
        orientation="h",
        title=(
            "Patient Voice Themes / "
            "환자 목소리 주제"
        ),
    )

    fig.update_layout(
        template="plotly_white",
        height=430,
        yaxis={
            "categoryorder": "total ascending"
        },
    )

    return fig


def run_patient_search(
    query,
    reddit_on,
    dcinside_on,
    patient_web_on,
):

    if not query.strip():

        return (
            pd.DataFrame(),
            build_theme_chart([]),
            "",
            [],
            "검색어를 입력해주세요.",
        )

    records, errors = (
        search_patient_voice(
            query=query,
            use_reddit=reddit_on,
            use_dcinside=dcinside_on,
            use_patient_web=(
                patient_web_on
            ),
            limit_per_source=30,
        )
    )

    analyzed, summary = (
        analyze_patient_voice(
            records
        )
    )

    summary_df = pd.DataFrame(
        summary
    )

    source_md = (
        build_source_results(
            analyzed
        )
    )

    source_counts = {}

    for item in analyzed:

        source = item.get(
            "source",
            "Unknown",
        )

        source_counts[source] = (
            source_counts.get(
                source,
                0,
            )
            + 1
        )

    status = f"""
### 검색 완료 / Search completed

**검색어 / Query:** `{query}`

**총 Patient Voice signal:** {len(analyzed)}

"""

    for source, count in (
        source_counts.items()
    ):

        status += (
            f"- {source}: **{count}**\n"
        )

    if errors:

        status += (
            "\n### 일부 Source 오류\n"
        )

        for error in errors:
            status += (
                f"- {error}\n"
            )

    return (
        summary_df,
        build_theme_chart(
            summary
        ),
        source_md,
        analyzed,
        status,
    )


def render_listen():

    gr.Markdown(
        """
# LISTEN / 듣기

외부의 질문과 경험을 수집하고
과학적 질문으로 연결합니다.

**HCP Insight / 의료진 인사이트**
+
**Patient Voice / 환자 목소리**
"""
    )

    with gr.Tabs():

        # ==================================================
        # HCP INSIGHTS
        # ==================================================

        with gr.Tab(
            "HCP INSIGHTS / 의료진 인사이트"
        ):

            gr.Markdown(
                """
## HCP Insight Capture / 의료진 인사이트 입력

실제 환자식별정보나 개인식별정보는 입력하지 않습니다.
"""
            )

            hcp_text = gr.Textbox(
                label=(
                    "Insight / "
                    "의료진 질문 또는 인사이트"
                ),
                placeholder=(
                    "예: 고령 환자에서 장기간 "
                    "치료 시 tolerability 관련 질문 증가"
                ),
                lines=5,
            )

            hcp_theme = gr.Dropdown(
                choices=[
                    "Patient Selection / 환자 선택",
                    "Biomarker / 바이오마커",
                    "Sequencing / 치료 순서",
                    "Safety / 안전성",
                    "Efficacy / 유효성",
                    "Treatment Duration / 치료기간",
                    "Unmet Need / 미충족 니즈",
                    "Other / 기타",
                ],
                label="Theme / 주제",
            )

            gr.Markdown(
                """
현재 단계에서는 HCP Insight는 입력과 분류까지만 제공합니다.
다음 CONNECT 단계에서 Evidence와 Patient Voice에 연결됩니다.
"""
            )

        # ==================================================
        # PATIENT VOICE
        # ==================================================

        with gr.Tab(
            "PATIENT VOICE / 환자 목소리"
        ):

            voice_state = gr.State(
                []
            )

            gr.Markdown(
                """
## Community Search / 커뮤니티 검색

공개적으로 접근 가능한 환자 생성 온라인 담론을 검색합니다.

검색 대상:
- Reddit
- DCInside 공개 색인 페이지
- 한국 환우회/환자회 관련 공개 웹페이지

**주의:** Patient Voice는 대표성 있는 환자 근거 또는
validated RWE가 아닙니다.
"""
            )

            query = gr.Textbox(
                label=(
                    "Keyword / 검색어"
                ),
                placeholder=(
                    "예: Jemperli, dostarlimab, "
                    "자궁내막암, multiple myeloma"
                ),
            )

            with gr.Row():

                reddit_toggle = gr.Checkbox(
                    value=True,
                    label=(
                        "Reddit"
                        + (
                            ""
                            if reddit_available()
                            else " (API key 필요)"
                        )
                    ),
                )

                dc_toggle = gr.Checkbox(
                    value=True,
                    label=(
                        "DCInside / 디시인사이드"
                        + (
                            ""
                            if naver_available()
                            else " (Naver API 필요)"
                        )
                    ),
                )

                patient_toggle = gr.Checkbox(
                    value=True,
                    label=(
                        "Patient Communities / "
                        "환우회·환자회"
                    ),
                )

            search_button = gr.Button(
                "SEARCH PATIENT VOICE / 환자 목소리 검색",
                variant="primary",
            )

            status = gr.Markdown()

            with gr.Row():

                with gr.Column(scale=4):

                    theme_df = gr.Dataframe(
                        headers=[
                            "Theme / 주제",
                            "Count / 건수",
                            "Share / 비율",
                        ],
                        interactive=False,
                        label=(
                            "Theme Summary / "
                            "주제 요약"
                        ),
                    )

                with gr.Column(scale=5):

                    theme_chart = gr.Plot(
                        value=(
                            build_theme_chart(
                                []
                            )
                        )
                    )

            gr.Markdown(
                """
## Source Posts / 원문 출처

제목을 클릭하면 해당 공개 원문으로 이동합니다.
"""
            )

            source_results = (
                gr.Markdown()
            )

            gr.Markdown(
                """
---

### Medical Affairs Use / 활용 원칙

Patient Voice는 다음을 탐색하기 위한
**hypothesis-generating signal**입니다.

- 치료 부담
- 부작용 경험
- 치료 지속/중단 이유
- 삶의 질
- 바이오마커 이해도
- 치료 순서에 대한 질문
- 접근성 및 비용
- 환자가 중요하게 생각하지만 임상시험에서 충분히 포착되지 않을 수 있는 문제

**Patient Voice signals are derived from self-selected public
online discussions and should not be interpreted as representative
patient evidence or validated RWE. They are intended for hypothesis
generation and Medical Affairs exploration only.**
"""
            )

            search_button.click(
                fn=run_patient_search,
                inputs=[
                    query,
                    reddit_toggle,
                    dc_toggle,
                    patient_toggle,
                ],
                outputs=[
                    theme_df,
                    theme_chart,
                    source_results,
                    voice_state,
                    status,
                ],
            )