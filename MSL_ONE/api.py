import json
import threading
import uuid

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from intelligence.patient_voice import (
    PATIENT_VOICE_DISCLAIMER,
    analyze_patient_voice,
)

from services.clinicaltrials import (
    search_trials_paginated,
)

from services.community import (
    search_patient_voice,
)

from services.dashboard import (
    build_live_dashboard,
    generate_pdf_report,
    generate_pptx_report,
)

from services.ema import (
    search_ema_medicines,
)

from services.fda import (
    fda_drugs_page,
    normalize_application,
    normalize_label,
    search_drugs_fda,
    search_fda_label,
)

from services.landscape import (
    build_treatment_landscape,
)

from services.pubmed import (
    search_pubmed_paginated,
)

from services.search_expander import (
    expand_search_query,
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="MSL ONE API",
    version="5.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


BASE_DIR = Path(__file__).resolve().parent

DATABASE_DIR = (
    BASE_DIR
    / "database"
)

DATABASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

HCP_FILE = (
    DATABASE_DIR
    / "hcp_insights.json"
)

HCP_LOCK = threading.Lock()


# ============================================================
# REQUEST MODELS
# ============================================================

class SearchRequest(BaseModel):
    query: str

    sources: List[str] = Field(
        default_factory=lambda: [
            "PubMed",
            "ClinicalTrials.gov",
            "FDA",
            "EMA",
        ]
    )

    page: int = 1
    page_size: int = 20


class ListenRequest(BaseModel):
    query: str

    sources: Optional[
        List[str]
    ] = None

    limit: int = 100


class LandscapeRequest(BaseModel):
    disease: str
    asset: str = ""
    setting: str = ""
    biomarker: str = ""


class DashboardRequest(BaseModel):
    company: str = "GSK"
    disease: str
    biomarker: str = ""
    setting: str = ""
    asset: str = ""


class HCPInsightRequest(BaseModel):
    topic: str
    observation: str
    insight_type: str

    source: str = (
        "HCP discussion"
    )

    meeting_date: str = ""
    notes: str = ""


class AnalyzeRequest(BaseModel):
    mode: str = "evidence"
    prompt: str = ""
    provider: str = "gemini"
    language: str = "한국어"

    evidence: List[
        Dict[str, Any]
    ] = Field(
        default_factory=list
    )

    listen: Optional[Any] = None

    hcp_insights: List[
        Dict[str, Any]
    ] = Field(
        default_factory=list
    )


class ReportExportRequest(BaseModel):
    report_type: str = "internal"
    language: str = "English"
    prompt: str = ""

    analysis_result: Any

    evidence: List[
        Dict[str, Any]
    ] = Field(
        default_factory=list
    )

    listen: Optional[
        Dict[str, Any]
    ] = None

    hcp_insights: List[
        Dict[str, Any]
    ] = Field(
        default_factory=list
    )

    metadata: Dict[
        str,
        Any,
    ] = Field(
        default_factory=dict
    )


# ============================================================
# HELPERS
# ============================================================

def _safe_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        list,
    ):
        return " · ".join(
            str(item)
            for item in value
            if item is not None
        )

    if isinstance(
        value,
        dict,
    ):
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
            )

        except Exception:
            return str(value)

    return str(
        value
    ).strip()


def _dedupe_records(
    records: List[
        Dict[str, Any]
    ],
) -> List[
    Dict[str, Any]
]:
    seen = set()
    result = []

    for record in records:
        source = _safe_text(
            record.get(
                "source"
            )
        ).lower()

        record_id = _safe_text(
            record.get(
                "id"
            )
            or
            record.get(
                "url"
            )
            or
            record.get(
                "title"
            )
        ).lower()

        key = (
            source,
            record_id,
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(
            record
        )

    return result


def _name_matches(
    candidate: str,
    terms: List[str],
) -> bool:
    candidate = (
        candidate
        or ""
    ).strip().lower()

    if not candidate:
        return False

    for term in terms:
        term = (
            term
            or ""
        ).strip().lower()

        if not term:
            continue

        if (
            term == candidate
            or
            term in candidate
            or
            candidate in term
        ):
            return True

    return False


# ============================================================
# FDA SEARCH HELPER
# ============================================================

def _fda_search(
    terms: List[str],
) -> List[
    Dict[str, Any]
]:
    label_results = []
    application_results = []

    for term in terms[:6]:
        try:
            raw_records = search_fda_label(
                term,
                limit=5,
            )

            for raw in raw_records:
                try:
                    normalized = normalize_label(
                        raw
                    )

                except Exception:
                    continue

                brand = _safe_text(
                    normalized.get(
                        "brand_name"
                    )
                )

                generic = _safe_text(
                    normalized.get(
                        "generic_name"
                    )
                )

                substance = _safe_text(
                    normalized.get(
                        "substance_name"
                    )
                )

                names = [
                    brand,
                    generic,
                    substance,
                ]

                if not any(
                    _name_matches(
                        name,
                        terms,
                    )
                    for name in names
                    if name
                ):
                    continue

                application = _safe_text(
                    normalized.get(
                        "application_number"
                    )
                )

                url = (
                    fda_drugs_page(
                        application
                    )
                    if application
                    else ""
                )

                if not url:
                    continue

                title_parts = []

                if brand:
                    title_parts.append(
                        brand
                    )

                if (
                    generic
                    and generic.lower()
                    not in [
                        item.lower()
                        for item in title_parts
                    ]
                ):
                    title_parts.append(
                        generic
                    )

                title = (
                    " — ".join(
                        title_parts
                    )
                    or term
                )

                label_results.append(
                    {
                        **normalized,
                        "source": "FDA",
                        "id": (
                            application
                            or
                            normalized.get(
                                "spl_set_id"
                            )
                            or
                            title
                        ),
                        "title": (
                            f"{title} — FDA label"
                        ),
                        "abstract": (
                            normalized.get(
                                "indications"
                            )
                            or
                            normalized.get(
                                "clinical_studies"
                            )
                            or
                            ""
                        ),
                        "journal": "FDA",
                        "status": "Regulatory",
                        "date": normalized.get(
                            "effective_time",
                            "",
                        ),
                        "url": url,
                    }
                )

        except Exception:
            continue

    for term in terms[:6]:
        try:
            raw_apps = search_drugs_fda(
                term,
                limit=6,
            )

            for raw in raw_apps:
                try:
                    normalized = normalize_application(
                        raw
                    )

                except Exception:
                    continue

                brand = _safe_text(
                    normalized.get(
                        "brand_name"
                    )
                )

                generic = _safe_text(
                    normalized.get(
                        "generic_name"
                    )
                )

                if not any(
                    _name_matches(
                        name,
                        terms,
                    )
                    for name in [
                        brand,
                        generic,
                    ]
                    if name
                ):
                    continue

                application = _safe_text(
                    normalized.get(
                        "application_number"
                    )
                )

                url = _safe_text(
                    normalized.get(
                        "url"
                    )
                )

                if not url:
                    continue

                title_parts = []

                if brand:
                    title_parts.append(
                        brand
                    )

                if generic:
                    title_parts.append(
                        generic
                    )

                title = (
                    " — ".join(
                        list(
                            dict.fromkeys(
                                title_parts
                            )
                        )
                    )
                    or
                    application
                )

                application_results.append(
                    {
                        **normalized,
                        "source": "FDA",
                        "id": application,
                        "title": (
                            f"{title} — Drugs@FDA"
                        ),
                        "abstract": (
                            "FDA application "
                            f"{application}"
                        ),
                        "journal": "FDA",
                        "status": "Regulatory",
                        "date": "",
                        "url": url,
                    }
                )

        except Exception:
            continue

    return _dedupe_records(
        [
            *label_results,
            *application_results,
        ]
    )[:10]


# ============================================================
# EMA SEARCH HELPER
# ============================================================

def _ema_search(
    terms: List[str],
) -> List[
    Dict[str, Any]
]:
    results = []

    for term in terms[:6]:
        try:
            candidates = search_ema_medicines(
                term,
                limit=8,
            )

            for item in candidates:
                names = [
                    _safe_text(
                        item.get(
                            "name"
                        )
                    ),
                    _safe_text(
                        item.get(
                            "brand_name"
                        )
                    ),
                    _safe_text(
                        item.get(
                            "generic_name"
                        )
                    ),
                    _safe_text(
                        item.get(
                            "active_substance"
                        )
                    ),
                ]

                if not any(
                    _name_matches(
                        name,
                        terms,
                    )
                    for name in names
                    if name
                ):
                    continue

                url = _safe_text(
                    item.get(
                        "url"
                    )
                    or
                    item.get(
                        "medicine_url"
                    )
                )

                if not url:
                    continue

                results.append(
                    {
                        **item,
                        "source": "EMA",
                        "status": (
                            item.get(
                                "status"
                            )
                            or
                            "Regulatory"
                        ),
                        "url": url,
                    }
                )

        except Exception:
            continue

    return _dedupe_records(
        results
    )[:10]


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "service": "MSL ONE",
        "status": "ok",
        "version": "4.1.0",
    }


# ============================================================
# LIVE HOME DASHBOARD
# ============================================================

@app.post("/dashboard")
def dashboard(
    request: DashboardRequest,
):
    disease = (
        request.disease
        or ""
    ).strip()

    if not disease:
        raise HTTPException(
            status_code=400,
            detail=(
                "Disease / indication "
                "is required."
            ),
        )

    try:
        return build_live_dashboard(
            company=request.company,
            disease=disease,
            biomarker=request.biomarker,
            setting=request.setting,
            asset=request.asset,
        )

    except Exception as exc:
        print(
            "[DASHBOARD]",
            type(exc).__name__,
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Live intelligence "
                "refresh failed: "
                f"{exc}"
            ),
        )


# ============================================================
# SEARCH
# ============================================================

@app.post("/search")
def search(
    request: SearchRequest,
):
    query = (
        request.query
        or ""
    ).strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail="Query is required.",
        )

    page = max(
        1,
        int(
            request.page
        ),
    )

    page_size = max(
        5,
        min(
            int(
                request.page_size
            ),
            50,
        ),
    )

    expanded = expand_search_query(
        query
    )

    requested_sources = {
        source.lower()
        for source in request.sources
    }

    pubmed_result = {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "total_pages": 0,
    }

    trial_result = {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "total_pages": 0,
    }

    fda_results = []
    ema_results = []
    source_errors = {}

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:
        futures = {}

        if "pubmed" in requested_sources:
            futures[
                "pubmed"
            ] = executor.submit(
                search_pubmed_paginated,
                expanded[
                    "pubmed_query"
                ],
                page,
                page_size,
            )

        if (
            "clinicaltrials.gov"
            in requested_sources
            or
            "clinicaltrials"
            in requested_sources
        ):
            futures[
                "trials"
            ] = executor.submit(
                search_trials_paginated,
                expanded[
                    "clinicaltrials_query"
                ],
                page,
                page_size,
            )

        if "fda" in requested_sources:
            futures[
                "fda"
            ] = executor.submit(
                _fda_search,
                expanded[
                    "regulatory_terms"
                ],
            )

        if "ema" in requested_sources:
            futures[
                "ema"
            ] = executor.submit(
                _ema_search,
                expanded[
                    "regulatory_terms"
                ],
            )

        for key, future in futures.items():
            try:
                value = future.result()

                if key == "pubmed":
                    pubmed_result = value

                elif key == "trials":
                    trial_result = value

                elif key == "fda":
                    fda_results = value

                elif key == "ema":
                    ema_results = value

            except Exception as exc:
                source_errors[
                    key
                ] = (
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

    regulatory_results = _dedupe_records(
        [
            *fda_results,
            *ema_results,
        ]
    )

    page_results = _dedupe_records(
        [
            *pubmed_result[
                "items"
            ],
            *trial_result[
                "items"
            ],
            *regulatory_results,
        ]
    )

    total_records = (
        int(
            pubmed_result[
                "total"
            ]
        )
        +
        int(
            trial_result[
                "total"
            ]
        )
        +
        len(
            regulatory_results
        )
    )

    return {
        "query": query,
        "search_terms_used": {
            "asset": expanded.get(
                "asset_term",
                "",
            ),
            "aliases": expanded.get(
                "aliases",
                [],
            ),
            "context": expanded.get(
                "context_terms",
                [],
            ),
            "display": expanded.get(
                "display_terms",
                [],
            ),
        },
        "source_queries": {
            "pubmed": expanded.get(
                "pubmed_query",
                "",
            ),
            "clinicaltrials": expanded.get(
                "clinicaltrials_query",
                "",
            ),
            "regulatory": expanded.get(
                "regulatory_terms",
                [],
            ),
        },
        "pubmed": pubmed_result[
            "items"
        ],
        "clinical_trials": trial_result[
            "items"
        ],
        "fda": fda_results,
        "ema": ema_results,
        "regulatory": regulatory_results,
        "results": page_results,
        "counts": {
            "peer_reviewed": pubmed_result[
                "total"
            ],
            "clinical_trials": trial_result[
                "total"
            ],
            "regulatory": len(
                regulatory_results
            ),
            "total": total_records,
        },
        "pagination": {
            "page": page,
            "page_size": page_size,
            "pubmed_total_pages": pubmed_result[
                "total_pages"
            ],
            "clinical_trials_total_pages": trial_result[
                "total_pages"
            ],
        },
        "source_status": {
            "pubmed": (
                "ok"
                if "pubmed"
                not in source_errors
                else "error"
            ),
            "clinicaltrials": (
                "ok"
                if "trials"
                not in source_errors
                else "error"
            ),
            "fda": (
                "ok"
                if "fda"
                not in source_errors
                else "error"
            ),
            "ema": (
                "ok"
                if "ema"
                not in source_errors
                else "error"
            ),
        },
        "source_errors": source_errors,
    }


# ============================================================
# LANDSCAPE
# ============================================================

@app.post("/landscape")
def landscape(
    request: LandscapeRequest,
):
    try:
        return build_treatment_landscape(
            disease=request.disease,
            asset=request.asset,
            setting=request.setting,
            biomarker=request.biomarker,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        print(
            "[LANDSCAPE]",
            type(exc).__name__,
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Treatment landscape "
                "generation failed."
            ),
        )


# ============================================================
# PATIENT VOICE
# ============================================================

@app.post("/listen")
def listen(
    request: ListenRequest,
):
    query = (
        request.query
        or ""
    ).strip()

    if not query:
        raise HTTPException(
            status_code=400,
            detail=(
                "Patient Voice query "
                "is required."
            ),
        )

    safe_limit = max(
        1,
        min(
            int(
                request.limit
                or 100
            ),
            100,
        ),
    )

    items_result = search_patient_voice(
        query=query,
        sources=request.sources,
        limit=safe_limit,
    )

    if isinstance(
        items_result,
        dict,
    ):
        items = (
            items_result.get(
                "items",
                [],
            )
            or []
        )

        source_status = (
            items_result.get(
                "source_status",
                {},
            )
            or {}
        )

        source_messages = (
            items_result.get(
                "source_messages",
                {},
            )
            or {}
        )

        source_details = (
            items_result.get(
                "source_details",
                {},
            )
            or {}
        )

        disclaimer = (
            items_result.get(
                "disclaimer",
                "",
            )
        )

    else:
        items = (
            items_result
            if isinstance(
                items_result,
                list,
            )
            else []
        )

        source_status = {}
        source_messages = {}
        source_details = {}
        disclaimer = ""

    analysis = analyze_patient_voice(
        items
    )

    return {
        "query": query,
        "items": analysis.get(
            "items",
            items,
        ),
        "count": analysis.get(
            "total_items",
            len(items),
        ),
        "total": analysis.get(
            "total_items",
            len(items),
        ),
        "analysis": analysis,
        "source_status": source_status,
        "source_messages": source_messages,
        "source_details": source_details,
        "disclaimer": (
            disclaimer
            or
            analysis.get(
                "disclaimer",
                PATIENT_VOICE_DISCLAIMER,
            )
        ),
    }


# ============================================================
# HCP INSIGHTS
# ============================================================

def _load_hcp_insights() -> List[
    Dict[str, Any]
]:
    if not HCP_FILE.exists():
        return []

    try:
        with HCP_FILE.open(
            "r",
            encoding="utf-8",
        ) as handle:
            payload = json.load(
                handle
            )

        if isinstance(
            payload,
            list,
        ):
            return payload

    except Exception:
        pass

    return []


def _save_hcp_insights(
    items: List[
        Dict[str, Any]
    ],
) -> None:
    with HCP_FILE.open(
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            items,
            handle,
            ensure_ascii=False,
            indent=2,
        )


@app.get("/hcp-insights")
def get_hcp_insights():
    with HCP_LOCK:
        items = _load_hcp_insights()

    return {
        "items": items,
        "count": len(items),
    }


@app.post("/hcp-insights")
def create_hcp_insight(
    request: HCPInsightRequest,
):
    topic = (
        request.topic
        or ""
    ).strip()

    observation = (
        request.observation
        or ""
    ).strip()

    if not topic:
        raise HTTPException(
            status_code=400,
            detail="Topic is required.",
        )

    if not observation:
        raise HTTPException(
            status_code=400,
            detail=(
                "Observation is required."
            ),
        )

    record = {
        "id": str(
            uuid.uuid4()
        ),
        "topic": topic,
        "observation": observation,
        "insight_type": (
            request.insight_type
            or ""
        ).strip(),
        "source": (
            (
                request.source
                or ""
            ).strip()
            or
            "HCP discussion"
        ),
        "meeting_date": (
            request.meeting_date
            or ""
        ).strip(),
        "notes": (
            request.notes
            or ""
        ).strip(),
        "signal_class": "F",
        "evidence_status": (
            "FIELD SIGNAL"
        ),
        "created_at": (
            datetime.now()
            .isoformat(
                timespec="seconds"
            )
        ),
    }

    with HCP_LOCK:
        items = _load_hcp_insights()

        items.insert(
            0,
            record,
        )

        _save_hcp_insights(
            items
        )

    return record


@app.delete(
    "/hcp-insights/{insight_id}"
)
def delete_hcp_insight(
    insight_id: str,
):
    with HCP_LOCK:
        items = _load_hcp_insights()

        updated = [
            item
            for item in items
            if item.get(
                "id"
            )
            != insight_id
        ]

        _save_hcp_insights(
            updated
        )

    return {
        "deleted": (
            len(updated)
            < len(items)
        )
    }


# ============================================================
# SOURCE CONTEXT
# ============================================================

def _source_context(
    evidence: List[
        Dict[str, Any]
    ],
) -> str:
    sections = []

    for index, item in enumerate(
        evidence,
        start=1,
    ):
        title = _safe_text(
            item.get(
                "title"
            )
        )

        source = _safe_text(
            item.get(
                "source"
            )
        )

        source_id = _safe_text(
            item.get(
                "id"
            )
            or
            item.get(
                "application_number"
            )
            or
            item.get(
                "pmid"
            )
            or
            item.get(
                "nct_id"
            )
        )

        url = _safe_text(
            item.get(
                "url"
            )
        )

        text = _safe_text(
            item.get(
                "abstract"
            )
            or
            item.get(
                "therapeutic_indication"
            )
            or
            item.get(
                "indications"
            )
            or
            item.get(
                "indication"
            )
            or
            item.get(
                "summary"
            )
        )

        text = text[:7000]

        sections.append(
            (
                f"[SOURCE {index}]\n"
                f"Source: {source}\n"
                f"ID: {source_id}\n"
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Text:\n{text}"
            )
        )

    return "\n\n".join(
        sections
    )


# ============================================================
# LLM ROUTER COMPATIBILITY
# ============================================================

def _call_llm(
    provider: str,
    system_prompt: str,
    user_prompt: str,
):
    from services import llm_router

    provider = (
        provider
        or ""
    ).strip().lower()

    combined_prompt = (
        system_prompt
        + "\n\n"
        + user_prompt
    )

    if provider == "gemini":
        candidates = [
            "generate_analysis",
            "ask_gemini",
        ]

    elif provider == "openai":
        candidates = [
            "generate_analysis",
            "ask_openai",
        ]

    else:
        candidates = [
            "generate_analysis",
        ]

    function = None

    for name in candidates:
        candidate = getattr(
            llm_router,
            name,
            None,
        )

        if candidate:
            function = candidate
            break

    if function is None:
        raise RuntimeError(
            (
                f"{provider} "
                "is not connected."
            )
        )

    attempts = [
        lambda: function(
            prompt=combined_prompt,
            provider=provider,
        ),
        lambda: function(
            provider=provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        ),
        lambda: function(
            system_prompt,
            user_prompt,
        ),
        lambda: function(
            combined_prompt
        ),
    ]

    last_error = None

    for attempt in attempts:
        try:
            return attempt()

        except TypeError as exc:
            last_error = exc
            continue

    if last_error:
        raise last_error

    raise RuntimeError(
        "LLM call failed."
    )


# ============================================================
# ANALYZE
# ============================================================

@app.post("/analyze")
def analyze(
    request: AnalyzeRequest,
):
    mode = (
        request.mode
        or "evidence"
    ).strip().lower()

    provider = (
        request.provider
        or "gemini"
    ).strip()

    language = (
        request.language
        or "한국어"
    ).strip()

    # --------------------------------------------------------
    # INSIGHT ANALYSIS
    # --------------------------------------------------------

    if mode == "listen":
        listen_payload = (
            request.listen
            or {}
        )

        if isinstance(
            listen_payload,
            dict,
        ):
            patient_items = (
                listen_payload.get(
                    "items",
                    [],
                )
                or []
            )

            patient_analysis = (
                listen_payload.get(
                    "analysis",
                    {},
                )
                or {}
            )

        elif isinstance(
            listen_payload,
            list,
        ):
            patient_items = (
                listen_payload
            )

            patient_analysis = {}

        else:
            patient_items = []
            patient_analysis = {}

        hcp_items = (
            request.hcp_insights
            or []
        )

        if (
            not patient_items
            and
            not patient_analysis
            and
            not hcp_items
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Patient Voice or HCP "
                    "signal material is required."
                ),
            )

        if (
            patient_items
            and
            not patient_analysis
        ):
            patient_analysis = (
                analyze_patient_voice(
                    patient_items
                )
            )

        if not isinstance(
            patient_analysis,
            dict,
        ):
            patient_analysis = {}

        signal_context = (
            patient_analysis.get(
                "llm_context",
                "",
            )
            or ""
        )

        representative_items = (
            patient_analysis.get(
                "representative_items",
                [],
            )
            or []
        )

        if not signal_context:
            signal_context = json.dumps(
                (
                    representative_items
                    or
                    patient_items[:16]
                ),
                ensure_ascii=False,
            )

        hcp_context = json.dumps(
            hcp_items,
            ensure_ascii=False,
        )

        system_prompt = """
You are MSL ONE's Medical Affairs insight analysis assistant.

The supplied inputs may contain Patient Voice signals and HCP field insights.

Strict scientific integrity rules:
- Patient Voice is derived from self-selected public online discussions.
- Patient Voice is NOT representative patient evidence.
- Patient Voice is NOT validated real-world evidence.
- HCP field insights are FIELD SIGNALS, not established scientific facts.
- Separate observation, interpretation, hypothesis and evidence gap.
- Never invent scientific evidence.
- Never invent regulatory status.
- Never create an unsupported answer to a potential HCP question.
- The purpose is scientific preparation and insight generation, not promotion.
- Do not create a sales script.

Produce a Medical Affairs Insight Analysis with:
1. Executive Summary
2. Major Emerging Themes
3. Patient Experience / Treatment Burden Signals
4. HCP Field Themes
5. Information Gaps / Unmet Needs
6. Potential HCP Scientific Questions
7. Evidence Readiness
   - Evidence available
   - Partial evidence
   - Evidence gap
8. Scientific Discussion Areas
9. Listen For
10. Questions to Explore
11. Post-Meeting Insight Capture Priorities
12. Limitations
""".strip()

        user_prompt = f"""
Response language:
{language}

User analysis question:
{request.prompt or "Identify the most important Medical Affairs insights, evidence gaps, likely HCP scientific questions and preparation priorities."}

PATIENT VOICE SIGNAL CONTEXT:
{signal_context}

HCP FIELD INSIGHTS:
{hcp_context}
""".strip()

    # --------------------------------------------------------
    # EVIDENCE ANALYSIS
    # --------------------------------------------------------

    else:
        if not request.evidence:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Selected evidence "
                    "is required."
                ),
            )

        context = _source_context(
            request.evidence
        )

        system_prompt = """
You are MSL ONE's source-grounded Medical Affairs evidence analysis assistant.

Use ONLY the supplied selected scientific sources.

Strict scientific integrity rules:
- Never invent efficacy results.
- Never invent safety results.
- Never invent statistical values.
- Never invent regulatory status.
- Never invent clinical-development facts.
- Every material scientific conclusion must be grounded in the supplied source set.
- If the supplied sources do not establish a point, explicitly state:
  "Not established from selected sources."
- Clearly distinguish regulatory evidence, peer-reviewed evidence and investigational evidence.
- Do not provide treatment recommendations.
- Do not claim superiority unless direct comparative evidence in the selected source set supports it.
- Cross-trial comparisons cannot establish superiority.
- Preserve source IDs and URLs in Source Trace.

Produce an Internal Medical Intelligence Analysis with:
1. Executive Summary
2. Scientific Context
3. Key Evidence Findings
4. Study / Population / Intervention / Comparator
5. Endpoints and Key Results
6. Safety Findings
7. Follow-up and Evidence Maturity
8. Cross-Evidence Synthesis
9. My Asset / Competitive Evidence Context
10. Evidence Gaps & Unanswered Questions
11. Medical Affairs Implications
12. Potential HCP Questions
13. Source Trace
14. Limitations
""".strip()

        user_prompt = f"""
Response language:
{language}

User analysis question:
{request.prompt or "Synthesize the selected evidence, identify evidence gaps and explain the Medical Affairs implications."}

SELECTED SOURCES:
{context}
""".strip()

    try:
        answer = _call_llm(
            provider=provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    except Exception as exc:
        print(
            "[ANALYZE]",
            type(exc).__name__,
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )

    return {
        "mode": mode,
        "provider": provider,
        "language": language,
        "answer": answer,
        "generated_at": (
            datetime.now()
            .isoformat(
                timespec="seconds"
            )
        ),
    }


# ============================================================
# ANALYSIS REPORT EXPORTS
# ============================================================

def _report_payload(
    request: ReportExportRequest,
) -> Dict[str, Any]:
    return {
        "prompt": request.prompt,
        "analysis_result": (
            request.analysis_result
        ),
        "evidence": request.evidence,
        "listen": (
            request.listen
            or {}
        ),
        "hcp_insights": (
            request.hcp_insights
        ),
        "metadata": (
            request.metadata
        ),
    }


@app.post(
    "/reports/export/pdf"
)
def report_export_pdf(
    request: ReportExportRequest,
):
    if not request.analysis_result:
        raise HTTPException(
            status_code=400,
            detail=(
                "Completed analysis "
                "is required before "
                "creating a report."
            ),
        )

    report_type = (
        request.report_type
        or "internal"
    ).strip().lower()

    if report_type not in {
        "internal",
        "hcp",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "report_type must be "
                "'internal' or 'hcp'."
            ),
        )

    try:
        path = generate_pdf_report(
            report=_report_payload(
                request
            ),
            report_type=report_type,
            language=request.language,
        )

        return FileResponse(
            path=str(path),
            media_type="application/pdf",
            filename=path.name,
        )

    except Exception as exc:
        print(
            "[REPORT PDF]",
            type(exc).__name__,
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "PDF report generation "
                f"failed: {exc}"
            ),
        )


@app.post(
    "/reports/export/pptx"
)
def report_export_pptx(
    request: ReportExportRequest,
):
    if not request.analysis_result:
        raise HTTPException(
            status_code=400,
            detail=(
                "Completed analysis "
                "is required before "
                "creating a report."
            ),
        )

    report_type = (
        request.report_type
        or "internal"
    ).strip().lower()

    if report_type not in {
        "internal",
        "hcp",
    }:
        raise HTTPException(
            status_code=400,
            detail=(
                "report_type must be "
                "'internal' or 'hcp'."
            ),
        )

    try:
        path = generate_pptx_report(
            report=_report_payload(
                request
            ),
            report_type=report_type,
            language=request.language,
        )

        return FileResponse(
            path=str(path),
            media_type=(
                "application/vnd."
                "openxmlformats-officedocument."
                "presentationml.presentation"
            ),
            filename=path.name,
        )

    except Exception as exc:
        print(
            "[REPORT PPTX]",
            type(exc).__name__,
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "PPTX report generation "
                f"failed: {exc}"
            ),
        )

# Preserve the original source and export endpoints; add the persistent workflow.
from workflow_api import make_router
app.include_router(make_router(globals()))
from cvrm_api import router as cvrm_router
app.include_router(cvrm_router)

