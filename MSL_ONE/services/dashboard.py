from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ============================================================
# PATHS / CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_DIR = BASE_DIR / "database"
DATABASE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

EXPORT_DIR = BASE_DIR / "generated_reports"
EXPORT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

HTTP_TIMEOUT = 20

USER_AGENT = (
    "MSL-ONE/4.1 "
    "Medical-Affairs-Intelligence"
)


# ============================================================
# GENERIC HELPERS
# ============================================================

def _now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds")
    )


def _safe(value: Any) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return " · ".join(
            _safe(item)
            for item in value
            if item is not None
        )

    if isinstance(value, dict):
        return " · ".join(
            f"{key}: {_safe(item)}"
            for key, item in value.items()
            if item not in (
                None,
                "",
                [],
                {},
            )
        )

    return str(value).strip()


def _compact(
    value: Any,
    limit: int = 700,
) -> str:
    text = re.sub(
        r"\s+",
        " ",
        _safe(value),
    ).strip()

    if len(text) <= limit:
        return text

    return text[: limit - 1].rstrip() + "…"


def _filename(value: str) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        value,
    )

    return cleaned.strip("_") or "MSL_ONE"


def _headers() -> Dict[str, str]:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }


def _source_state(
    status: str,
    refreshed_at: str = "",
    message: str = "",
) -> Dict[str, str]:
    return {
        "status": status,
        "refreshed_at": refreshed_at,
        "message": message,
    }


def _dedupe(
    items: List[Dict[str, Any]],
    keys: List[str],
) -> List[Dict[str, Any]]:
    seen = set()
    result = []

    for item in items:
        key = tuple(
            _safe(
                item.get(field)
            ).lower()
            for field in keys
        )

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def _escape_pdf(value: Any) -> str:
    return html.escape(
        _safe(value)
    )


# ============================================================
# FDA
# ============================================================

def _fetch_fda_landscape(
    disease: str,
    biomarker: str,
) -> List[Dict[str, Any]]:
    queries = [disease]

    if biomarker:
        queries.insert(
            0,
            f"{disease} {biomarker}",
        )

    results = []

    for term in queries:
        try:
            response = requests.get(
                "https://api.fda.gov/drug/label.json",
                params={
                    "search": (
                        "indications_and_usage:"
                        f'"{term}"'
                    ),
                    "limit": 50,
                },
                headers=_headers(),
                timeout=HTTP_TIMEOUT,
            )

            if response.status_code == 404:
                continue

            response.raise_for_status()

            raw_items = (
                response.json()
                .get(
                    "results",
                    [],
                )
                or []
            )

            for raw in raw_items:
                openfda = (
                    raw.get(
                        "openfda",
                        {},
                    )
                    or {}
                )

                indication = _safe(
                    raw.get(
                        "indications_and_usage",
                        [],
                    )
                )

                brand = _safe(
                    openfda.get(
                        "brand_name",
                        [],
                    )
                )

                generic = _safe(
                    openfda.get(
                        "generic_name",
                        [],
                    )
                )

                manufacturer = _safe(
                    openfda.get(
                        "manufacturer_name",
                        [],
                    )
                )

                application = _safe(
                    openfda.get(
                        "application_number",
                        [],
                    )
                )

                effective = _safe(
                    raw.get(
                        "effective_time",
                        "",
                    )
                )

                app_number = re.sub(
                    r"\D",
                    "",
                    application,
                )

                if app_number:
                    url = (
                        "https://www.accessdata.fda.gov/"
                        "scripts/cder/daf/"
                        "index.cfm?"
                        "event=overview.process"
                        f"&ApplNo={app_number}"
                    )
                else:
                    url = (
                        "https://www.accessdata.fda.gov/"
                        "scripts/cder/daf/"
                    )

                results.append(
                    {
                        "id": (
                            application
                            or brand
                            or generic
                        ),
                        "brand": brand,
                        "generic": generic,
                        "manufacturer": manufacturer,
                        "application_number": application,
                        "effective_time": effective,
                        "indication": _compact(
                            indication,
                            1200,
                        ),
                        "status": "FDA label record",
                        "source": "FDA",
                        "url": url,
                    }
                )

        except Exception:
            continue

    return _dedupe(
        results,
        [
            "application_number",
            "brand",
            "generic",
        ],
    )[:30]


# ============================================================
# PUBMED
# ============================================================

def _fetch_pubmed(
    disease: str,
    biomarker: str,
    setting: str,
) -> List[Dict[str, Any]]:
    query = " ".join(
        item
        for item in [
            disease,
            biomarker,
            setting,
        ]
        if item
    )

    search_response = requests.get(
        (
            "https://eutils.ncbi.nlm.nih.gov/"
            "entrez/eutils/esearch.fcgi"
        ),
        params={
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": 10,
            "sort": "pub date",
        },
        headers=_headers(),
        timeout=HTTP_TIMEOUT,
    )

    search_response.raise_for_status()

    ids = (
        search_response.json()
        .get(
            "esearchresult",
            {},
        )
        .get(
            "idlist",
            [],
        )
        or []
    )

    if not ids:
        return []

    summary_response = requests.get(
        (
            "https://eutils.ncbi.nlm.nih.gov/"
            "entrez/eutils/esummary.fcgi"
        ),
        params={
            "db": "pubmed",
            "id": ",".join(ids),
            "retmode": "json",
        },
        headers=_headers(),
        timeout=HTTP_TIMEOUT,
    )

    summary_response.raise_for_status()

    payload = (
        summary_response.json()
        .get(
            "result",
            {},
        )
    )

    items = []

    for pmid in ids:
        record = (
            payload.get(
                pmid,
                {},
            )
            or {}
        )

        items.append(
            {
                "id": pmid,
                "source": "PubMed",
                "title": _safe(
                    record.get(
                        "title"
                    )
                ),
                "journal": _safe(
                    record.get(
                        "fulljournalname"
                    )
                    or
                    record.get(
                        "source"
                    )
                ),
                "date": _safe(
                    record.get(
                        "pubdate"
                    )
                ),
                "abstract": (
                    "Open the PubMed record "
                    "for full study details."
                ),
                "url": (
                    "https://pubmed.ncbi.nlm.nih.gov/"
                    f"{pmid}/"
                ),
            }
        )

    return items


# ============================================================
# CLINICALTRIALS.GOV
# ============================================================

def _fetch_trials(
    disease: str,
    biomarker: str,
    setting: str,
) -> List[Dict[str, Any]]:
    query = " ".join(
        item
        for item in [
            disease,
            biomarker,
            setting,
        ]
        if item
    )

    response = requests.get(
        (
            "https://clinicaltrials.gov/"
            "api/v2/studies"
        ),
        params={
            "query.term": query,
            "pageSize": 40,
            "format": "json",
        },
        headers=_headers(),
        timeout=HTTP_TIMEOUT,
    )

    response.raise_for_status()

    studies = (
        response.json()
        .get(
            "studies",
            [],
        )
        or []
    )

    items = []

    for study in studies:
        protocol = (
            study.get(
                "protocolSection",
                {},
            )
            or {}
        )

        identification = (
            protocol.get(
                "identificationModule",
                {},
            )
            or {}
        )

        status = (
            protocol.get(
                "statusModule",
                {},
            )
            or {}
        )

        design = (
            protocol.get(
                "designModule",
                {},
            )
            or {}
        )

        conditions = (
            protocol.get(
                "conditionsModule",
                {},
            )
            or {}
        )

        interventions_module = (
            protocol.get(
                "armsInterventionsModule",
                {},
            )
            or {}
        )

        sponsor_module = (
            protocol.get(
                "sponsorCollaboratorsModule",
                {},
            )
            or {}
        )

        nct = _safe(
            identification.get(
                "nctId"
            )
        )

        interventions = []

        for intervention in (
            interventions_module.get(
                "interventions",
                [],
            )
            or []
        ):
            name = _safe(
                intervention.get(
                    "name"
                )
            )

            if name:
                interventions.append(
                    name
                )

        lead_sponsor = (
            sponsor_module.get(
                "leadSponsor",
                {},
            )
            or {}
        )

        items.append(
            {
                "id": nct,
                "source": "ClinicalTrials.gov",
                "title": _safe(
                    identification.get(
                        "briefTitle"
                    )
                ),
                "phase": (
                    _safe(
                        design.get(
                            "phases",
                            [],
                        )
                    )
                    or
                    "Not specified"
                ),
                "status": (
                    _safe(
                        status.get(
                            "overallStatus"
                        )
                    )
                    or
                    "Unknown"
                ),
                "population": _safe(
                    conditions.get(
                        "conditions",
                        [],
                    )
                ),
                "target": (
                    biomarker
                    or
                    "Not specified"
                ),
                "interventions": interventions,
                "sponsor": _safe(
                    lead_sponsor.get(
                        "name"
                    )
                ),
                "url": (
                    "https://clinicaltrials.gov/"
                    f"study/{nct}"
                    if nct
                    else
                    "https://clinicaltrials.gov/"
                ),
            }
        )

    return items


# ============================================================
# COMPANY SNAPSHOT
# ============================================================

def _company_sources(
    company: str,
) -> List[Dict[str, str]]:
    if company.upper() != "GSK":
        return []

    return [
        {
            "label": "GSK Pipeline",
            "url": (
                "https://www.gsk.com/"
                "en-gb/innovation/pipeline/"
            ),
        },
        {
            "label": "GSK Products",
            "url": (
                "https://www.gsk.com/"
                "en-gb/products/products-a-z/"
            ),
        },
    ]


def _gsk_pipeline_snapshot() -> List[Dict[str, Any]]:
    return [
        {
            "id": "zidesamtinib",
            "asset": "zidesamtinib",
            "target": "ROS1",
            "population": "ROS1-positive NSCLC",
            "phase": "See current company source",
            "status": "Verify current status",
            "source": "GSK Pipeline",
            "url": (
                "https://www.gsk.com/"
                "en-gb/innovation/pipeline/"
            ),
        },
        {
            "id": "neladalkib",
            "asset": "neladalkib",
            "target": "ALK",
            "population": "ALK-positive NSCLC",
            "phase": "See current company source",
            "status": "Verify current status",
            "source": "GSK Pipeline",
            "url": (
                "https://www.gsk.com/"
                "en-gb/innovation/pipeline/"
            ),
        },
        {
            "id": "NVL-330",
            "asset": "NVL-330",
            "target": "HER2",
            "population": "HER2-altered solid tumors",
            "phase": "See current company source",
            "status": "Verify current status",
            "source": "GSK Pipeline",
            "url": (
                "https://www.gsk.com/"
                "en-gb/innovation/pipeline/"
            ),
        },
    ]


def _filter_company_pipeline(
    company: str,
    disease: str,
    biomarker: str,
) -> List[Dict[str, Any]]:
    if company.upper() != "GSK":
        return []

    records = _gsk_pipeline_snapshot()
    result = []

    disease_lower = (
        disease
        or ""
    ).strip().lower()

    biomarker_lower = (
        biomarker
        or ""
    ).strip().lower()

    for item in records:
        searchable = " ".join(
            [
                _safe(
                    item.get(
                        "asset"
                    )
                ),
                _safe(
                    item.get(
                        "target"
                    )
                ),
                _safe(
                    item.get(
                        "population"
                    )
                ),
            ]
        ).lower()

        if (
            disease_lower
            and
            disease_lower not in searchable
        ):
            continue

        if (
            biomarker_lower
            and
            biomarker_lower not in searchable
        ):
            continue

        result.append(item)

    return result


def _company_products_from_fda(
    company: str,
    fda_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    aliases = {
        "GSK": [
            "gsk",
            "glaxosmithkline",
            "glaxo smith kline",
        ]
    }

    company_terms = aliases.get(
        company.upper(),
        [
            company.lower()
        ],
    )

    items = []

    for item in fda_items:
        manufacturer = _safe(
            item.get(
                "manufacturer"
            )
        ).lower()

        if not any(
            term in manufacturer
            for term in company_terms
        ):
            continue

        items.append(
            {
                "id": item.get(
                    "id"
                ),
                "brand": item.get(
                    "brand"
                ),
                "generic": item.get(
                    "generic"
                ),
                "application_number": item.get(
                    "application_number"
                ),
                "url": item.get(
                    "url"
                ),
            }
        )

    return items


# ============================================================
# ASSET POSITION
# ============================================================

def _build_asset_position(
    asset: str,
    biomarker: str,
    setting: str,
    fda_items: List[Dict[str, Any]],
    company_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not asset:
        return {
            "my_asset": None,
            "comparators": [],
            "comparison_note": (
                "Select My Asset "
                "to build this view."
            ),
        }

    asset_lower = asset.lower()
    my_asset = None

    for item in fda_items:
        names = (
            _safe(
                item.get(
                    "brand"
                )
            )
            + " "
            +
            _safe(
                item.get(
                    "generic"
                )
            )
        ).lower()

        if asset_lower in names:
            my_asset = {
                "name": asset,
                "position_type": "FDA label match",
                "status": "FDA label record",
                "url": item.get(
                    "url"
                ),
            }
            break

    if my_asset is None:
        for item in company_items:
            names = (
                _safe(
                    item.get(
                        "asset"
                    )
                )
                + " "
                +
                _safe(
                    item.get(
                        "id"
                    )
                )
            ).lower()

            if asset_lower in names:
                my_asset = {
                    "name": asset,
                    "position_type": (
                        "Company source match"
                    ),
                    "status": item.get(
                        "status"
                    ),
                    "phase": item.get(
                        "phase"
                    ),
                    "url": item.get(
                        "url"
                    ),
                }
                break

    if my_asset is None:
        my_asset = {
            "name": asset,
            "position_type": (
                "User-selected asset"
            ),
            "status": (
                "Not established "
                "from current sources"
            ),
        }

    comparators = []

    for item in fda_items[:5]:
        names = (
            _safe(
                item.get(
                    "brand"
                )
            )
            + " "
            +
            _safe(
                item.get(
                    "generic"
                )
            )
        ).lower()

        if asset_lower in names:
            continue

        comparators.append(
            {
                "brand": item.get(
                    "brand"
                ),
                "generic": item.get(
                    "generic"
                ),
                "status": "FDA label record",
                "biomarker": (
                    biomarker
                    or
                    "See label"
                ),
                "setting": (
                    setting
                    or
                    "See label"
                ),
                "url": item.get(
                    "url"
                ),
            }
        )

    return {
        "my_asset": my_asset,
        "comparators": comparators,
        "comparison_note": (
            "No direct comparative evidence "
            "identified by this dashboard. "
            "Cross-trial comparisons cannot "
            "establish superiority."
        ),
    }


# ============================================================
# WHAT CHANGED
# ============================================================

def _build_changes(
    fda_items: List[Dict[str, Any]],
    trials: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    changes = []

    for item in fda_items[:3]:
        changes.append(
            {
                "type": "FDA",
                "title": (
                    item.get(
                        "brand"
                    )
                    or
                    item.get(
                        "generic"
                    )
                    or
                    "FDA record"
                ),
                "detail": _compact(
                    item.get(
                        "indication"
                    ),
                    300,
                ),
                "date": item.get(
                    "effective_time"
                ),
                "url": item.get(
                    "url"
                ),
            }
        )

    for item in trials[:2]:
        changes.append(
            {
                "type": "TRIAL",
                "title": item.get(
                    "title"
                ),
                "detail": (
                    f"{_safe(item.get('phase'))}"
                    " · "
                    f"{_safe(item.get('status'))}"
                ),
                "date": "",
                "url": item.get(
                    "url"
                ),
            }
        )

    for item in evidence[:2]:
        changes.append(
            {
                "type": "PAPER",
                "title": item.get(
                    "title"
                ),
                "detail": item.get(
                    "journal"
                ),
                "date": item.get(
                    "date"
                ),
                "url": item.get(
                    "url"
                ),
            }
        )

    return changes


# ============================================================
# LIVE DASHBOARD
# ============================================================

def build_live_dashboard(
    company: str = "GSK",
    disease: str = "",
    biomarker: str = "",
    setting: str = "",
    asset: str = "",
) -> Dict[str, Any]:
    disease = (
        disease
        or ""
    ).strip()

    biomarker = (
        biomarker
        or ""
    ).strip()

    setting = (
        setting
        or ""
    ).strip()

    asset = (
        asset
        or ""
    ).strip()

    company = (
        company
        or "GSK"
    ).strip()

    if not disease:
        raise ValueError(
            "Disease / indication is required."
        )

    source_status = {
        "FDA": _source_state(
            "not-run"
        ),
        "ClinicalTrials.gov": _source_state(
            "not-run"
        ),
        "PubMed": _source_state(
            "not-run"
        ),
        "Company source": _source_state(
            "not-run"
        ),
    }

    successes = []

    try:
        fda_items = _fetch_fda_landscape(
            disease,
            biomarker,
        )

        refreshed = _now_iso()

        source_status["FDA"] = _source_state(
            "ok",
            refreshed,
            (
                f"{len(fda_items)} "
                "label records"
            ),
        )

        successes.append(
            refreshed
        )

    except Exception as exc:
        fda_items = []

        source_status["FDA"] = _source_state(
            "error",
            "",
            str(exc),
        )

    try:
        trials = _fetch_trials(
            disease,
            biomarker,
            setting,
        )

        refreshed = _now_iso()

        source_status[
            "ClinicalTrials.gov"
        ] = _source_state(
            "ok",
            refreshed,
            (
                f"{len(trials)} "
                "studies"
            ),
        )

        successes.append(
            refreshed
        )

    except Exception as exc:
        trials = []

        source_status[
            "ClinicalTrials.gov"
        ] = _source_state(
            "error",
            "",
            str(exc),
        )

    try:
        evidence = _fetch_pubmed(
            disease,
            biomarker,
            setting,
        )

        refreshed = _now_iso()

        source_status["PubMed"] = _source_state(
            "ok",
            refreshed,
            (
                f"{len(evidence)} "
                "records"
            ),
        )

        successes.append(
            refreshed
        )

    except Exception as exc:
        evidence = []

        source_status["PubMed"] = _source_state(
            "error",
            "",
            str(exc),
        )

    try:
        company_pipeline = _filter_company_pipeline(
            company,
            disease,
            biomarker,
        )

        refreshed = _now_iso()

        source_status[
            "Company source"
        ] = _source_state(
            "ok",
            refreshed,
            (
                f"{len(company_pipeline)} "
                "matching assets"
            ),
        )

        successes.append(
            refreshed
        )

    except Exception as exc:
        company_pipeline = []

        source_status[
            "Company source"
        ] = _source_state(
            "error",
            "",
            str(exc),
        )

    company_products = _company_products_from_fda(
        company,
        fda_items,
    )

    company_asset_names = {
        _safe(
            item.get(
                "asset"
            )
        ).lower()
        for item in company_pipeline
        if item.get(
            "asset"
        )
    }

    competitor_pipeline = []

    for trial in trials:
        intervention_text = _safe(
            trial.get(
                "interventions"
            )
        ).lower()

        if any(
            asset_name in intervention_text
            for asset_name in company_asset_names
            if asset_name
        ):
            continue

        competitor_pipeline.append(
            trial
        )

    return {
        "company": company,
        "disease": disease,
        "biomarker": biomarker,
        "setting": setting,
        "asset": asset,
        "last_successful_refresh": (
            max(successes)
            if successes
            else None
        ),
        "source_status": source_status,
        "company_products": company_products,
        "current_treatment_landscape": (
            fda_items
        ),
        "asset_position": _build_asset_position(
            asset,
            biomarker,
            setting,
            fda_items,
            company_pipeline,
        ),
        "company_pipeline": company_pipeline,
        "competitor_pipeline": (
            competitor_pipeline[:15]
        ),
        "what_changed": _build_changes(
            fda_items,
            trials,
            evidence,
        ),
        "latest_scientific_evidence": (
            evidence
        ),
        "sources": [
            {
                "label": "FDA / Drugs@FDA",
                "url": (
                    "https://www.accessdata.fda.gov/"
                    "scripts/cder/daf/"
                ),
            },
            {
                "label": "ClinicalTrials.gov",
                "url": (
                    "https://clinicaltrials.gov/"
                ),
            },
            {
                "label": "PubMed",
                "url": (
                    "https://pubmed.ncbi.nlm.nih.gov/"
                ),
            },
            *_company_sources(
                company
            ),
        ],
        "limitations": [
            (
                "FDA label search results are "
                "not clinical guidelines."
            ),
            (
                "ClinicalTrials.gov records are "
                "investigational unless approval "
                "is separately verified."
            ),
            (
                "No superiority conclusion should "
                "be drawn from cross-trial "
                "comparisons."
            ),
        ],
    }


# ============================================================
# REPORT NORMALIZATION
# ============================================================

def _analysis_answer(
    report: Dict[str, Any],
) -> str:
    result = (
        report.get(
            "analysis_result",
            {}
        )
        or {}
    )

    if isinstance(
        result,
        str,
    ):
        return result

    if isinstance(
        result,
        dict,
    ):
        answer = (
            result.get(
                "answer"
            )
            or
            result.get(
                "analysis"
            )
        )

        if answer:
            return _safe(
                answer
            )

        return _safe(
            result
        )

    return _safe(
        result
    )


def _source_record(
    item: Dict[str, Any],
) -> Dict[str, str]:
    source_id = _safe(
        item.get(
            "id"
        )
        or
        item.get(
            "application_number"
        )
        or
        item.get(
            "nct_id"
        )
        or
        item.get(
            "pmid"
        )
    )

    title = _safe(
        item.get(
            "title"
        )
        or
        item.get(
            "brand"
        )
        or
        item.get(
            "name"
        )
        or
        "Untitled source"
    )

    detail = _safe(
        item.get(
            "abstract"
        )
        or
        item.get(
            "indication"
        )
        or
        item.get(
            "therapeutic_indication"
        )
        or
        item.get(
            "observation"
        )
        or
        item.get(
            "summary"
        )
    )

    return {
        "source": (
            _safe(
                item.get(
                    "source"
                )
            )
            or
            "Source"
        ),
        "id": source_id,
        "title": title,
        "url": _safe(
            item.get(
                "url"
            )
        ),
        "detail": _compact(
            detail,
            700,
        ),
    }


def _analysis_lines(
    answer: str,
) -> List[str]:
    lines = []

    for raw in (
        answer
        or ""
    ).splitlines():
        line = raw.strip()

        if not line:
            continue

        cleaned = re.sub(
            r"^[#>*\-\s]+",
            "",
            line,
        ).strip()

        if cleaned:
            lines.append(
                cleaned
            )

    return lines


# ============================================================
# INTERNAL REPORT CONTENT
# ============================================================

def _internal_sections(
    report: Dict[str, Any],
) -> List[Dict[str, Any]]:
    evidence = (
        report.get(
            "evidence",
            [],
        )
        or []
    )

    answer = _analysis_answer(
        report
    )

    prompt = _safe(
        report.get(
            "prompt"
        )
    )

    metadata = (
        report.get(
            "metadata",
            {},
        )
        or {}
    )

    source_records = [
        _source_record(
            item
        )
        for item in evidence
    ]

    analysis_lines = _analysis_lines(
        answer
    )

    key_lines = (
        analysis_lines[:12]
        if analysis_lines
        else [
            "Analysis result unavailable."
        ]
    )

    return [
        {
            "title": "Executive Summary",
            "text": answer,
        },
        {
            "title": "Scientific Context",
            "bullets": [
                (
                    "Analysis question: "
                    + (
                        prompt
                        or
                        "Not specified"
                    )
                ),
                (
                    "Selected evidence: "
                    f"{len(evidence)} source(s)"
                ),
                (
                    "Provider: "
                    + _safe(
                        metadata.get(
                            "provider"
                        )
                    )
                ),
                (
                    "Analysis language: "
                    + _safe(
                        metadata.get(
                            "language"
                        )
                    )
                ),
            ],
        },
        {
            "title": "Key Evidence Findings",
            "sources": source_records,
        },
        {
            "title": "Cross-Evidence Synthesis",
            "bullets": key_lines,
        },
        {
            "title": (
                "My Asset / Competitive "
                "Evidence Context"
            ),
            "bullets": [
                (
                    "Only evidence contained in "
                    "the selected source set should "
                    "be used for comparative context."
                ),
                (
                    "No direct comparative evidence "
                    "identified unless explicitly "
                    "supported by a selected source."
                ),
                (
                    "Cross-trial comparisons cannot "
                    "establish superiority."
                ),
            ],
        },
        {
            "title": (
                "Evidence Gaps & "
                "Unanswered Questions"
            ),
            "text": (
                "Use the evidence analysis above "
                "to identify missing comparative "
                "evidence, immature follow-up, "
                "subgroup uncertainty, safety "
                "uncertainty, biomarker questions "
                "and unanswered scientific questions."
            ),
        },
        {
            "title": "Medical Affairs Implications",
            "text": (
                "Translate source-grounded findings "
                "into scientific monitoring needs, "
                "future insight-collection priorities, "
                "evidence-generation questions and "
                "potential topics for scientific "
                "exchange. This report is not a "
                "treatment recommendation."
            ),
        },
        {
            "title": "Source Trace & Limitations",
            "sources": source_records,
            "bullets": [
                (
                    "Verify each original publication, "
                    "trial record and regulatory source "
                    "before external scientific use."
                ),
                (
                    "Investigational evidence must not "
                    "be presented as approved treatment."
                ),
                (
                    "Absence of evidence in the selected "
                    "source set does not prove absence "
                    "of evidence elsewhere."
                ),
            ],
        },
    ]


# ============================================================
# HCP BRIEF CONTENT
# ============================================================

def _hcp_sections(
    report: Dict[str, Any],
) -> List[Dict[str, Any]]:
    listen = (
        report.get(
            "listen",
            {},
        )
        or {}
    )

    hcp_insights = (
        report.get(
            "hcp_insights",
            [],
        )
        or []
    )

    answer = _analysis_answer(
        report
    )

    patient_items = (
        listen.get(
            "items",
            [],
        )
        if isinstance(
            listen,
            dict,
        )
        else []
    )

    patient_analysis = (
        listen.get(
            "analysis",
            {},
        )
        if isinstance(
            listen,
            dict,
        )
        else {}
    )

    if not isinstance(
        patient_analysis,
        dict,
    ):
        patient_analysis = {}

    top_themes = (
        patient_analysis.get(
            "top_themes",
            [],
        )
        or []
    )

    theme_summary = (
        patient_analysis.get(
            "theme_summary",
            ""
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

    source_items = (
        representative_items
        if representative_items
        else patient_items[:16]
    )

    source_records = [
        _source_record(
            item
        )
        for item in source_items[:16]
    ]

    hcp_records = [
        {
            "source": (
                item.get(
                    "source"
                )
                or
                "HCP discussion"
            ),
            "id": item.get(
                "id",
                "",
            ),
            "title": item.get(
                "topic",
                "HCP Insight",
            ),
            "url": "",
            "detail": item.get(
                "observation",
                "",
            ),
        }
        for item in hcp_insights[:20]
    ]

    analysis_lines = _analysis_lines(
        answer
    )

    return [
        {
            "title": (
                "Meeting Preparation Snapshot"
            ),
            "bullets": [
                (
                    "Patient Voice signals "
                    f"available: {len(patient_items)}"
                ),
                (
                    "Representative Patient Voice "
                    f"signals: {len(source_items)}"
                ),
                (
                    "Saved HCP field insights: "
                    f"{len(hcp_insights)}"
                ),
                (
                    "Field signals are inputs for "
                    "hypothesis generation and "
                    "scientific preparation."
                ),
            ],
        },
        {
            "title": "Emerging Field Themes",
            "text": _safe(
                theme_summary
            ),
            "bullets": [
                _safe(
                    item
                )
                for item in top_themes[:10]
                if _safe(
                    item
                )
            ],
        },
        {
            "title": "What HCPs May Ask",
            "text": answer,
        },
        {
            "title": "Evidence Readiness",
            "bullets": [
                (
                    "Evidence available — question "
                    "can be addressed from validated "
                    "scientific sources."
                ),
                (
                    "Partial evidence — evidence exists "
                    "but important population, follow-up "
                    "or comparative limitations remain."
                ),
                (
                    "Evidence gap — do not create an "
                    "unsupported scientific answer."
                ),
            ],
        },
        {
            "title": "Scientific Discussion Points",
            "bullets": (
                analysis_lines[:12]
                if analysis_lines
                else [
                    (
                        "Use the completed Insight "
                        "Analysis to prepare scientific "
                        "discussion areas."
                    )
                ]
            ),
        },
        {
            "title": "Listen For",
            "bullets": [
                "Treatment-selection factors",
                "Sequencing concerns",
                "Biomarker-testing barriers",
                "Safety concerns",
                "Unmet needs",
                "Evidence requests",
                (
                    "Clinical scenarios where current "
                    "evidence is insufficient"
                ),
            ],
        },
        {
            "title": "Questions to Explore",
            "bullets": [
                (
                    "Which evidence gaps most affect "
                    "clinical decision-making?"
                ),
                (
                    "Which patient populations still "
                    "have meaningful unmet need?"
                ),
                (
                    "Which data could change treatment "
                    "selection or sequencing decisions?"
                ),
                (
                    "Which evidence would be most useful "
                    "in future scientific exchange?"
                ),
            ],
        },
        {
            "title": "Post-Meeting Insight Capture",
            "bullets": [
                "New HCP Insight",
                "Evidence Request",
                "Unmet Need",
                "Emerging Scientific Question",
                "Follow-up Required",
            ],
        },
        {
            "title": "Patient Voice Signal Trace",
            "sources": source_records,
        },
        {
            "title": "HCP Field Insight Trace",
            "sources": hcp_records,
        },
        {
            "title": "Limitations",
            "bullets": [
                (
                    "Patient Voice signals derive from "
                    "self-selected public online "
                    "discussions."
                ),
                (
                    "Patient Voice must not be "
                    "interpreted as representative "
                    "patient evidence or validated RWE."
                ),
                (
                    "HCP insights are field signals "
                    "and are not established scientific "
                    "facts."
                ),
                (
                    "The HCP Discussion Brief is for "
                    "scientific preparation and is not "
                    "a promotional script."
                ),
            ],
        },
    ]


def _report_title(
    report_type: str,
) -> str:
    if (
        report_type
        or ""
    ).lower() == "hcp":
        return "HCP Discussion Brief"

    return (
        "Internal Medical "
        "Intelligence Report"
    )


def _report_sections(
    report: Dict[str, Any],
    report_type: str,
) -> List[Dict[str, Any]]:
    metadata = report.get("metadata") or {}
    if metadata.get("workflow_output"):
        korean = metadata.get("language") == "kr"
        return [
            {"title": ("근거 바구니 분석" if korean else "Evidence Basket Analysis") if metadata.get("basket_analysis") else "HCP 미팅 브리프" if korean and report_type == "hcp" else "내부 메디컬 인텔리전스" if korean else "HCP Meeting Brief" if report_type == "hcp" else "Internal Medical Intelligence", "text": _analysis_answer(report)},
            {"title": "출처 추적" if korean else "Source Trace", "sources": [_source_record(item) for item in report.get("evidence", [])]},
            {"title": "제한 사항" if korean else "Limitations", "bullets": ["메디컬 검토 필요. 출처 원문을 확인하세요. 공개 신호는 검증된 임상 근거가 아닙니다. 치료 권고가 아닙니다." if korean else "Medical review required. Verify original sources. Public signals are not validated clinical evidence. No treatment recommendations."]},
        ]
    if (
        report_type
        or ""
    ).lower() == "hcp":
        return _hcp_sections(
            report
        )

    return _internal_sections(
        report
    )


# ============================================================
# PDF FONT
# ============================================================

def _register_pdf_fonts() -> Dict[str, str]:
    font_paths = [
        (
            "Malgun",
            "C:/Windows/Fonts/malgun.ttf",
        ),
        (
            "MalgunBold",
            "C:/Windows/Fonts/malgunbd.ttf",
        ),
    ]

    result = {
        "regular": "Helvetica",
        "bold": "Helvetica-Bold",
    }

    for name, path_text in font_paths:
        path = Path(
            path_text
        )

        if not path.exists():
            continue

        try:
            pdfmetrics.registerFont(
                TTFont(
                    name,
                    str(path),
                )
            )

            if name == "Malgun":
                result["regular"] = name

            if name == "MalgunBold":
                result["bold"] = name

        except Exception:
            continue

    return result


# ============================================================
# PDF
# ============================================================

def generate_pdf_report(
    report: Dict[str, Any],
    report_type: str = "internal",
    language: str = "English",
) -> Path:
    title = _report_title(
        report_type
    )

    stamp = (
        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    path = (
        EXPORT_DIR
        /
        (
            _filename(
                title
            )
            + "_"
            + stamp
            + ".pdf"
        )
    )

    fonts = _register_pdf_fonts()

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "MSLOneTitle",
        parent=styles["Title"],
        fontName=fonts["bold"],
        fontSize=20,
        leading=25,
        textColor=colors.HexColor(
            "#17233F"
        ),
        spaceAfter=8,
    )

    kicker_style = ParagraphStyle(
        "MSLOneKicker",
        parent=styles["BodyText"],
        fontName=fonts["bold"],
        fontSize=7,
        leading=10,
        textColor=colors.HexColor(
            "#315FD5"
        ),
        spaceAfter=4,
    )

    heading_style = ParagraphStyle(
        "MSLOneHeading",
        parent=styles["Heading2"],
        fontName=fonts["bold"],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor(
            "#315FD5"
        ),
        spaceBefore=10,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "MSLOneBody",
        parent=styles["BodyText"],
        fontName=fonts["regular"],
        fontSize=8.2,
        leading=12.2,
        textColor=colors.HexColor(
            "#46546A"
        ),
        spaceAfter=5,
    )

    small_style = ParagraphStyle(
        "MSLOneSmall",
        parent=styles["BodyText"],
        fontName=fonts["regular"],
        fontSize=6.7,
        leading=9.5,
        textColor=colors.HexColor(
            "#6E7889"
        ),
        spaceAfter=3,
    )

    document = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=title,
        author="MSL ONE",
    )

    story = [
        Paragraph(
            (
                "MSL ONE · MEDICAL AFFAIRS "
                "INTELLIGENCE"
            ),
            kicker_style,
        ),
        Paragraph(
            _escape_pdf(
                title
            ),
            title_style,
        ),
        Paragraph(
            _escape_pdf(
                (
                    "Generated "
                    + datetime.now().strftime(
                        "%d %b %Y · %H:%M"
                    )
                    + " · "
                    + language
                )
            ),
            small_style,
        ),
        Spacer(
            1,
            6,
        ),
    ]

    sections = _report_sections(
        report,
        report_type,
    )

    for section_index, section in enumerate(
        sections
    ):
        if (
            section_index > 0
            and section.get(
                "page_break"
            )
        ):
            story.append(
                PageBreak()
            )

        story.append(
            Paragraph(
                _escape_pdf(
                    section.get(
                        "title",
                        "",
                    )
                ),
                heading_style,
            )
        )

        section_text = _safe(
            section.get(
                "text"
            )
        )

        if section_text:
            for paragraph_text in (
                section_text
                .splitlines()
            ):
                paragraph_text = (
                    paragraph_text
                    .strip()
                )

                if not paragraph_text:
                    continue

                story.append(
                    Paragraph(
                        _escape_pdf(
                            paragraph_text
                        ),
                        body_style,
                    )
                )

        for bullet in (
            section.get(
                "bullets",
                [],
            )
            or []
        ):
            bullet_text = _safe(
                bullet
            )

            if not bullet_text:
                continue

            story.append(
                Paragraph(
                    (
                        "• "
                        + _escape_pdf(
                            bullet_text
                        )
                    ),
                    body_style,
                )
            )

        source_rows = (
            section.get(
                "sources",
                [],
            )
            or []
        )

        if source_rows:
            rows = [
                [
                    Paragraph(
                        "<b>Source</b>",
                        small_style,
                    ),
                    Paragraph(
                        "<b>Title / Detail</b>",
                        small_style,
                    ),
                    Paragraph(
                        "<b>ID / URL</b>",
                        small_style,
                    ),
                ]
            ]

            for source in source_rows[:30]:
                source_name = _escape_pdf(
                    source.get(
                        "source"
                    )
                )

                source_title = _escape_pdf(
                    _compact(
                        source.get(
                            "title"
                        ),
                        220,
                    )
                )

                source_detail = _escape_pdf(
                    _compact(
                        source.get(
                            "detail"
                        ),
                        420,
                    )
                )

                source_id = _escape_pdf(
                    source.get(
                        "id"
                    )
                )

                source_url = _escape_pdf(
                    _compact(
                        source.get(
                            "url"
                        ),
                        260,
                    )
                )

                title_detail = (
                    f"<b>{source_title}</b>"
                )

                if source_detail:
                    title_detail += (
                        "<br/>"
                        + source_detail
                    )

                id_url = source_id

                if source_url:
                    if id_url:
                        id_url += "<br/>"

                    id_url += source_url

                rows.append(
                    [
                        Paragraph(
                            source_name,
                            small_style,
                        ),
                        Paragraph(
                            title_detail,
                            small_style,
                        ),
                        Paragraph(
                            id_url,
                            small_style,
                        ),
                    ]
                )

            table = Table(
                rows,
                colWidths=[
                    27 * mm,
                    88 * mm,
                    55 * mm,
                ],
                repeatRows=1,
            )

            table.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (
                                0,
                                0,
                            ),
                            (
                                -1,
                                0,
                            ),
                            colors.HexColor(
                                "#EEF4FF"
                            ),
                        ),
                        (
                            "GRID",
                            (
                                0,
                                0,
                            ),
                            (
                                -1,
                                -1,
                            ),
                            0.3,
                            colors.HexColor(
                                "#DCE3EE"
                            ),
                        ),
                        (
                            "VALIGN",
                            (
                                0,
                                0,
                            ),
                            (
                                -1,
                                -1,
                            ),
                            "TOP",
                        ),
                        (
                            "LEFTPADDING",
                            (
                                0,
                                0,
                            ),
                            (
                                -1,
                                -1,
                            ),
                            4,
                        ),
                        (
                            "RIGHTPADDING",
                            (
                                0,
                                0,
                            ),
                            (
                                -1,
                                -1,
                            ),
                            4,
                        ),
                        (
                            "TOPPADDING",
                            (
                                0,
                                0,
                            ),
                            (
                                -1,
                                -1,
                            ),
                            4,
                        ),
                        (
                            "BOTTOMPADDING",
                            (
                                0,
                                0,
                            ),
                            (
                                -1,
                                -1,
                            ),
                            4,
                        ),
                    ]
                )
            )

            story.append(
                table
            )

        story.append(
            Spacer(
                1,
                3,
            )
        )

    story.extend(
        [
            Spacer(
                1,
                10,
            ),
            Paragraph(
                (
                    "MSL ONE · Scientific preparation "
                    "and Medical Affairs use. Verify "
                    "original sources before external "
                    "scientific exchange."
                ),
                small_style,
            ),
        ]
    )

    document.build(
        story
    )

    return path


# ============================================================
# PPTX HELPERS
# ============================================================

def _ppt_add_title(
    slide,
    title: str,
    subtitle: str = "",
):
    title_box = slide.shapes.add_textbox(
        Inches(0.7),
        Inches(0.5),
        Inches(11.8),
        Inches(0.75),
    )

    paragraph = (
        title_box
        .text_frame
        .paragraphs[0]
    )

    paragraph.text = title
    paragraph.font.name = "Malgun Gothic"
    paragraph.font.size = Pt(24)
    paragraph.font.bold = True
    paragraph.font.color.rgb = RGBColor(
        23,
        35,
        63,
    )

    if subtitle:
        subtitle_box = (
            slide.shapes
            .add_textbox(
                Inches(0.72),
                Inches(1.25),
                Inches(11.5),
                Inches(0.4),
            )
        )

        subtitle_paragraph = (
            subtitle_box
            .text_frame
            .paragraphs[0]
        )

        subtitle_paragraph.text = subtitle
        subtitle_paragraph.font.name = (
            "Malgun Gothic"
        )
        subtitle_paragraph.font.size = Pt(9)
        subtitle_paragraph.font.color.rgb = RGBColor(
            104,
            116,
            137,
        )


def _ppt_add_footer(
    slide,
):
    footer = slide.shapes.add_textbox(
        Inches(0.7),
        Inches(7.05),
        Inches(11.8),
        Inches(0.25),
    )

    paragraph = (
        footer
        .text_frame
        .paragraphs[0]
    )

    paragraph.text = (
        "MSL ONE · MEDICAL AFFAIRS INTELLIGENCE"
    )

    paragraph.font.name = "Malgun Gothic"
    paragraph.font.size = Pt(6.5)
    paragraph.font.color.rgb = RGBColor(
        140,
        149,
        162,
    )


def _ppt_section_lines(
    section: Dict[str, Any],
) -> List[str]:
    lines = []

    text = _safe(
        section.get(
            "text"
        )
    )

    if text:
        for raw in text.splitlines():
            raw = raw.strip()

            if raw:
                lines.append(
                    raw
                )

    for bullet in (
        section.get(
            "bullets",
            [],
        )
        or []
    ):
        bullet_text = _safe(
            bullet
        )

        if bullet_text:
            lines.append(
                "• " + bullet_text
            )

    for source in (
        section.get(
            "sources",
            [],
        )
        or []
    )[:10]:
        title = _safe(
            source.get(
                "title"
            )
        )

        source_name = _safe(
            source.get(
                "source"
            )
        )

        source_id = _safe(
            source.get(
                "id"
            )
        )

        label = title

        trace = " · ".join(
            item
            for item in [
                source_name,
                source_id,
            ]
            if item
        )

        if trace:
            label += (
                "\n   "
                + trace
            )

        lines.append(
            "• " + label
        )

    return lines


def _ppt_add_content(
    slide,
    section: Dict[str, Any],
):
    lines = _ppt_section_lines(
        section
    )

    if not lines:
        lines = [
            (
                "No source-grounded "
                "content available."
            )
        ]

    box = slide.shapes.add_textbox(
        Inches(0.78),
        Inches(1.8),
        Inches(11.55),
        Inches(5.0),
    )

    frame = box.text_frame
    frame.word_wrap = True
    frame.clear()

    visible_lines = lines[:18]

    for index, line in enumerate(
        visible_lines
    ):
        paragraph = (
            frame.paragraphs[0]
            if index == 0
            else
            frame.add_paragraph()
        )

        paragraph.text = _compact(
            line,
            850,
        )

        paragraph.font.name = (
            "Malgun Gothic"
        )

        paragraph.font.size = Pt(
            10.5
            if len(
                visible_lines
            ) <= 10
            else 8.8
        )

        paragraph.font.color.rgb = RGBColor(
            68,
            82,
            106,
        )

        paragraph.space_after = Pt(6)


# ============================================================
# PPTX
# ============================================================

def generate_pptx_report(
    report: Dict[str, Any],
    report_type: str = "internal",
    language: str = "English",
) -> Path:
    title = _report_title(
        report_type
    )

    stamp = (
        datetime.now()
        .strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    path = (
        EXPORT_DIR
        /
        (
            _filename(
                title
            )
            + "_"
            + stamp
            + ".pptx"
        )
    )

    presentation = Presentation()

    presentation.slide_width = Inches(
        13.333
    )

    presentation.slide_height = Inches(
        7.5
    )

    blank_layout = (
        presentation
        .slide_layouts[6]
    )

    cover = presentation.slides.add_slide(
        blank_layout
    )

    kicker_box = (
        cover.shapes
        .add_textbox(
            Inches(0.9),
            Inches(1.25),
            Inches(11.2),
            Inches(0.4),
        )
    )

    kicker = (
        kicker_box
        .text_frame
        .paragraphs[0]
    )

    kicker.text = (
        "MSL ONE · MEDICAL AFFAIRS INTELLIGENCE"
    )

    kicker.font.name = "Malgun Gothic"
    kicker.font.size = Pt(10)
    kicker.font.bold = True
    kicker.font.color.rgb = RGBColor(
        49,
        95,
        213,
    )

    cover_title_box = (
        cover.shapes
        .add_textbox(
            Inches(0.9),
            Inches(2.0),
            Inches(11.2),
            Inches(1.2),
        )
    )

    cover_title = (
        cover_title_box
        .text_frame
        .paragraphs[0]
    )

    cover_title.text = title
    cover_title.font.name = (
        "Malgun Gothic"
    )
    cover_title.font.size = Pt(30)
    cover_title.font.bold = True
    cover_title.font.color.rgb = RGBColor(
        23,
        35,
        63,
    )

    descriptor_box = (
        cover.shapes
        .add_textbox(
            Inches(0.92),
            Inches(3.5),
            Inches(10.8),
            Inches(1.0),
        )
    )

    descriptor = (
        descriptor_box
        .text_frame
        .paragraphs[0]
    )

    if (
        report_type
        or ""
    ).lower() == "hcp":
        descriptor.text = (
            "Insight Analysis → "
            "HCP Scientific Preparation"
        )
    else:
        descriptor.text = (
            "Evidence Analysis → "
            "Internal Medical Intelligence"
        )

    descriptor.font.name = "Malgun Gothic"
    descriptor.font.size = Pt(14)
    descriptor.font.color.rgb = RGBColor(
        82,
        97,
        122,
    )

    generated_box = (
        cover.shapes
        .add_textbox(
            Inches(0.92),
            Inches(4.4),
            Inches(10.8),
            Inches(0.5),
        )
    )

    generated = (
        generated_box
        .text_frame
        .paragraphs[0]
    )

    generated.text = (
        datetime.now().strftime(
            "%d %b %Y · %H:%M"
        )
        + " · "
        + language
    )

    generated.font.name = "Malgun Gothic"
    generated.font.size = Pt(9)
    generated.font.color.rgb = RGBColor(
        120,
        130,
        145,
    )

    _ppt_add_footer(
        cover
    )

    for section in _report_sections(
        report,
        report_type,
    ):
        slide = presentation.slides.add_slide(
            blank_layout
        )

        _ppt_add_title(
            slide,
            section.get(
                "title",
                "",
            ),
            title,
        )

        _ppt_add_content(
            slide,
            section,
        )

        _ppt_add_footer(
            slide
        )

    presentation.save(
        str(path)
    )

    return path
