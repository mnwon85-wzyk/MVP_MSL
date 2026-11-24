# app.py

import gradio as gr

from pages.search import render_search
from pages.listen import render_listen


# ============================================================
# LIGHT THEME - FORCE GRADIO 6 TO STAY LIGHT
# ============================================================

CSS = """
/* ==========================================================
   MSL ONE DESIGN SYSTEM
========================================================== */

:root,
.dark {
    color-scheme: light !important;

    --body-background-fill: #f6f8fb !important;
    --background-fill-primary: #ffffff !important;
    --background-fill-secondary: #f7f9fc !important;

    --block-background-fill: #ffffff !important;
    --block-border-color: #dce5ef !important;
    --block-label-background-fill: #ffffff !important;
    --block-label-text-color: #17233b !important;
    --block-title-text-color: #17233b !important;

    --input-background-fill: #ffffff !important;
    --input-border-color: #cad6e4 !important;

    --body-text-color: #17233b !important;
    --body-text-color-subdued: #687a94 !important;

    --button-secondary-background-fill: #f7f9fc !important;
    --button-secondary-text-color: #53647e !important;

    --table-even-background-fill: #ffffff !important;
    --table-odd-background-fill: #f8fafc !important;
}


/* ==========================================================
   GLOBAL RESET
========================================================== */

html,
body,
.gradio-container {
    color-scheme: light !important;
    background: #f6f8fb !important;
    color: #17233b !important;
}

body {
    margin: 0 !important;
}

.gradio-container {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;

    font-family:
        Inter,
        "Pretendard",
        "Noto Sans KR",
        "Segoe UI",
        Arial,
        sans-serif !important;
}


/* ==========================================================
   FORCE ALL GRADIO BLOCKS LIGHT
========================================================== */

.gradio-container .block,
.gradio-container .form,
.gradio-container .wrap,
.gradio-container .panel,
.gradio-container .container,
.gradio-container .block-container {
    color: #17233b !important;
}

.gradio-container input,
.gradio-container textarea,
.gradio-container select {
    background: #ffffff !important;
    color: #17233b !important;
    border-color: #cad6e4 !important;
}

.gradio-container input::placeholder,
.gradio-container textarea::placeholder {
    color: #8796aa !important;
}


/* ==========================================================
   APP SHELL
========================================================== */

#app-shell {
    gap: 0 !important;
    align-items: stretch !important;
}

#sidebar {
    background: #f3f6fa !important;
    border-right: 1px solid #e5ebf2 !important;

    min-width: 220px !important;
    max-width: 220px !important;

    padding: 30px 16px !important;
}

#workspace {
    background: #ffffff !important;
    padding: 0 34px 50px 34px !important;

    min-width: 0 !important;
}


/* ==========================================================
   BRAND
========================================================== */

.brand-wrap {
    padding: 8px 10px 48px 10px;
}

.brand-name {
    color: #0b1f3a !important;

    font-size: 29px;
    line-height: 1;
    font-weight: 800;

    letter-spacing: -0.7px;
}

.brand-subtitle {
    color: #647795 !important;

    margin-top: 10px;

    font-size: 14px;
    line-height: 1.5;
}


/* ==========================================================
   SIDEBAR NAV
========================================================== */

.nav-btn {
    min-height: 48px !important;

    justify-content: flex-start !important;

    padding-left: 16px !important;

    margin-bottom: 8px !important;

    border: 0 !important;
    border-radius: 11px !important;

    background: transparent !important;

    color: #405575 !important;

    font-size: 14px !important;
    font-weight: 550 !important;

    box-shadow: none !important;
}

.nav-btn:hover {
    background: #e8eff8 !important;
    color: #174f9d !important;
}

.nav-active {
    background: #dceaff !important;
    color: #1762c6 !important;
    font-weight: 750 !important;
}

.sidebar-bottom {
    margin-top: 250px;

    padding-left: 10px;

    color: #667c9b !important;

    font-family: Georgia, serif;
    font-size: 13px;
    font-style: italic;
    line-height: 1.5;
}


/* ==========================================================
   TOP BAR
========================================================== */

.topbar {
    height: 72px;

    display: flex;
    justify-content: flex-end;
    align-items: center;

    gap: 20px;

    border-bottom: 1px solid #edf1f5;
}

.topbar-tag {
    color: #64748b !important;

    font-family: Georgia, serif;
    font-style: italic;

    font-size: 13px;
}

.user-chip {
    display: flex;
    align-items: center;

    gap: 9px;

    background: #f5f7fa;

    color: #42536d !important;

    padding: 9px 14px;

    border-radius: 24px;

    font-size: 14px;
}

.user-dot {
    width: 7px;
    height: 7px;

    background: #25466d;

    border-radius: 50%;
}


/* ==========================================================
   PAGE HEADER
========================================================== */

.page-header {
    margin-top: 27px;
    margin-bottom: 21px;
}

.page-title {
    color: #0a1e3c !important;

    font-size: 34px;
    line-height: 1.08;

    font-weight: 800;

    letter-spacing: -0.8px;
}

.page-subtitle {
    color: #667991 !important;

    font-size: 16px;

    margin-top: 6px;
}


/* ==========================================================
   SEARCH TOP CARDS
========================================================== */

.search-card {
    background: #ffffff !important;

    border: 1px solid #dce5ef !important;

    border-radius: 14px !important;

    padding: 20px !important;

    box-shadow: 0 2px 10px rgba(31, 49, 79, 0.04) !important;
}

.search-card *,
.search-card .block,
.search-card .form,
.search-card .wrap {
    color: #17233b !important;
}

.section-title {
    color: #112746 !important;

    font-size: 18px;
    font-weight: 750;
}

.section-help {
    color: #708199 !important;

    font-size: 13px;

    margin-top: 4px;
}


/* ==========================================================
   SOURCE CARDS
========================================================== */

.source-grid {
    display: grid;

    grid-template-columns: 1fr 1fr;

    gap: 11px;

    margin-top: 17px;
}

.source-tile {
    min-height: 90px;

    display: flex;
    flex-direction: column;
    justify-content: center;

    padding: 16px;

    background: #ffffff;

    border: 1px solid #cfdeee;

    border-radius: 11px;
}

.source-header {
    display: flex;

    gap: 9px;

    align-items: center;
}

.source-icon {
    width: 32px;
    height: 32px;

    display: flex;
    align-items: center;
    justify-content: center;

    background: #edf4ff;

    border-radius: 8px;

    color: #1762c6 !important;
}

.source-icon svg {
    width: 18px;
    height: 18px;
}

.source-title {
    color: #153a68 !important;

    font-size: 15px;
    font-weight: 750;
}

.source-description {
    margin-top: 7px;

    color: #75869d !important;

    font-size: 12px;
}


/* ==========================================================
   CHECKBOX GROUP - FORCE LIGHT
========================================================== */

.source-checkboxes {
    margin-top: 14px !important;
}

.source-checkboxes,
.source-checkboxes > div,
.source-checkboxes .wrap,
.source-checkboxes label {
    background: transparent !important;
}

.source-checkboxes label {
    color: #40536e !important;
}

.source-checkboxes input {
    accent-color: #1764d2 !important;
}


/* ==========================================================
   QUERY
========================================================== */

.query-box textarea {
    min-height: 92px !important;

    background: #ffffff !important;

    color: #17233b !important;

    border: 1px solid #cbd7e4 !important;

    border-radius: 9px !important;

    font-size: 14px !important;
}

.example-text {
    color: #75849a !important;

    font-size: 12px;

    margin-top: 10px;
}


/* ==========================================================
   BUTTONS
========================================================== */

#search-button {
    background: #1764d2 !important;

    color: #ffffff !important;

    border: 1px solid #1764d2 !important;

    font-weight: 700 !important;
}

#search-button * {
    color: #ffffff !important;
}

#reset-button {
    background: #f7f9fc !important;

    color: #52637b !important;

    border: 1px solid #d5dee9 !important;

    font-weight: 650 !important;
}


/* ==========================================================
   SEARCH RESULTS
========================================================== */

.result-divider {
    margin: 24px 0 14px 0;

    border-top: 1px solid #d9e2ec;
}

.result-heading {
    color: #102544 !important;

    font-size: 24px;
    font-weight: 800;
}

.result-help {
    color: #758399 !important;

    font-size: 13px;

    margin-top: 4px;
    margin-bottom: 12px;
}


/* ==========================================================
   METRIC BOXES
========================================================== */

.metric-input input {
    background: #ffffff !important;

    color: #17233b !important;

    border: 1px solid #d4dee9 !important;
}


/* ==========================================================
   ACCORDIONS
========================================================== */

.gradio-accordion {
    background: #ffffff !important;

    border: 1px solid #d4e0ed !important;

    border-radius: 12px !important;

    overflow: hidden !important;
}

.gradio-accordion > .label-wrap {
    background: #edf5ff !important;

    color: #174879 !important;

    padding: 14px !important;

    font-weight: 700 !important;
}

.regulatory-accordion > .label-wrap {
    background: #ecf8f3 !important;

    color: #17644f !important;
}

.gradio-accordion .content,
.gradio-accordion .content > div,
.gradio-accordion .wrap {
    background: #ffffff !important;

    color: #23364f !important;
}


/* ==========================================================
   MARKDOWN
========================================================== */

.prose,
.prose p,
.prose li,
.prose strong,
.prose span,
.prose h1,
.prose h2,
.prose h3,
.prose h4 {
    color: #22354e !important;
}

.prose a {
    color: #1763bf !important;

    text-decoration: none;
}

.prose a:hover {
    text-decoration: underline;
}


/* ==========================================================
   TABLE
========================================================== */

table {
    color-scheme: light !important;

    background: #ffffff !important;

    color: #24364f !important;

    border-color: #dce5ef !important;
}

table th {
    background: #f1f5f9 !important;

    color: #1f3553 !important;
}

table td {
    background: #ffffff !important;

    color: #24364f !important;
}


/* ==========================================================
   TIPS
========================================================== */

.tips-card {
    margin-top: 19px;

    background: #fafcff;

    border: 1px solid #d8e2ec;

    border-radius: 11px;

    padding: 16px 18px;

    color: #53677f !important;

    font-size: 12px;

    overflow: hidden;
}

.tips-title {
    color: #213651 !important;

    font-weight: 750;

    font-size: 13px;
}

.tips-signature {
    float: right;

    text-align: right;

    color: #6c7d93 !important;

    font-family: Georgia, serif;
    font-style: italic;
}


/* ==========================================================
   RESPONSIVE
========================================================== */

@media (max-width: 1000px) {

    #sidebar {
        min-width: 180px !important;
        max-width: 180px !important;
    }

    #workspace {
        padding-left: 20px !important;
        padding-right: 20px !important;
    }

    .source-grid {
        grid-template-columns: 1fr;
    }
}
"""


# ============================================================
# PAGE SWITCHING
# ============================================================

def switch_page(target):

    return (
        gr.update(visible=target == "search"),
        gr.update(visible=target == "listen"),
        gr.update(visible=target == "analysis"),
        gr.update(visible=target == "export"),
        gr.update(visible=target == "sources"),
    )


# ============================================================
# APP
# ============================================================

with gr.Blocks(
    title="MSL ONE",
    theme=gr.themes.Base(),
    css=CSS,
) as app:

    with gr.Row(elem_id="app-shell"):

        # ====================================================
        # SIDEBAR
        # ====================================================

        with gr.Column(
            elem_id="sidebar",
            scale=0,
        ):

            gr.HTML(
                """
                <div class="brand-wrap">

                    <div class="brand-name">
                        MSL ONE
                    </div>

                    <div class="brand-subtitle">
                        Insights for<br>
                        Greater Impact
                    </div>

                </div>
                """
            )

            btn_search = gr.Button(
                "Smart Search",
                elem_classes=["nav-btn", "nav-active"],
            )

            btn_listen = gr.Button(
                "Listen",
                elem_classes=["nav-btn"],
            )

            btn_analysis = gr.Button(
                "Summary & Analysis",
                elem_classes=["nav-btn"],
            )

            btn_export = gr.Button(
                "Export",
                elem_classes=["nav-btn"],
            )

            btn_sources = gr.Button(
                "Source Center",
                elem_classes=["nav-btn"],
            )

            gr.HTML(
                """
                <div class="sidebar-bottom">

                    Science<br>
                    Patients<br>
                    A Greater Tomorrow

                </div>
                """
            )

        # ====================================================
        # MAIN WORKSPACE
        # ====================================================

        with gr.Column(
            elem_id="workspace",
            scale=1,
        ):

            gr.HTML(
                """
                <div class="topbar">

                    <div class="topbar-tag">
                        From Evidence to Impact
                    </div>

                    <div class="user-chip">
                        <div class="user-dot"></div>
                        MSL
                        <span>⌄</span>
                    </div>

                </div>
                """
            )

            # ------------------------------------------------
            # SEARCH
            # ------------------------------------------------

            with gr.Column(
                visible=True,
            ) as page_search:

                render_search()

            # ------------------------------------------------
            # LISTEN
            # ------------------------------------------------

            with gr.Column(
                visible=False,
            ) as page_listen:

                render_listen()

            # ------------------------------------------------
            # ANALYSIS
            # ------------------------------------------------

            with gr.Column(
                visible=False,
            ) as page_analysis:

                gr.HTML(
                    """
                    <div class="page-header">

                        <div class="page-title">
                            3. SUMMARY & ANALYSIS
                        </div>

                        <div class="page-subtitle">
                            Evidence, external insights and
                            Medical Intelligence in one report.
                        </div>

                    </div>
                    """
                )

            # ------------------------------------------------
            # EXPORT
            # ------------------------------------------------

            with gr.Column(
                visible=False,
            ) as page_export:

                gr.HTML(
                    """
                    <div class="page-header">

                        <div class="page-title">
                            4. EXPORT
                        </div>

                        <div class="page-subtitle">
                            Create Word, PDF and PowerPoint reports.
                        </div>

                    </div>
                    """
                )

            # ------------------------------------------------
            # SOURCES
            # ------------------------------------------------

            with gr.Column(
                visible=False,
            ) as page_sources:

                gr.HTML(
                    """
                    <div class="page-header">

                        <div class="page-title">
                            5. SOURCE CENTER
                        </div>

                        <div class="page-subtitle">
                            Verify source provenance,
                            status and traceability.
                        </div>

                    </div>
                    """
                )

    # ========================================================
    # NAV EVENTS
    # ========================================================

    btn_search.click(
        lambda: switch_page("search"),
        outputs=[
            page_search,
            page_listen,
            page_analysis,
            page_export,
            page_sources,
        ],
    )

    btn_listen.click(
        lambda: switch_page("listen"),
        outputs=[
            page_search,
            page_listen,
            page_analysis,
            page_export,
            page_sources,
        ],
    )

    btn_analysis.click(
        lambda: switch_page("analysis"),
        outputs=[
            page_search,
            page_listen,
            page_analysis,
            page_export,
            page_sources,
        ],
    )

    btn_export.click(
        lambda: switch_page("export"),
        outputs=[
            page_search,
            page_listen,
            page_analysis,
            page_export,
            page_sources,
        ],
    )

    btn_sources.click(
        lambda: switch_page("sources"),
        outputs=[
            page_search,
            page_listen,
            page_analysis,
            page_export,
            page_sources,
        ],
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    print("=" * 55)
    print("MSL ONE")
    print("http://127.0.0.1:7860")
    print("=" * 55)

    app.launch(
        server_name="127.0.0.1",
        server_port=7860,
        show_error=True,
    )