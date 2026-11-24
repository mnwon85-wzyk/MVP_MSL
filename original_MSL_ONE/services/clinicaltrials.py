from typing import Any, Dict, List, Optional

import requests


API_URL = "https://clinicaltrials.gov/api/v2/studies"
TIMEOUT = 30


def _safe_dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _safe_list(value) -> list:
    return value if isinstance(value, list) else []


def _normalize_interventions(study: dict) -> List[Dict[str, str]]:
    protocol = _safe_dict(study.get("protocolSection"))

    arms = _safe_dict(
        protocol.get("armsInterventionsModule")
    )

    interventions = []

    for item in _safe_list(arms.get("interventions")):
        if not isinstance(item, dict):
            continue

        name = str(item.get("name") or "").strip()
        intervention_type = str(
            item.get("type") or ""
        ).strip()

        if not name:
            continue

        interventions.append(
            {
                "name": name,
                "type": intervention_type,
            }
        )

    return interventions


def normalize_trial(study: dict) -> Dict[str, Any]:
    protocol = _safe_dict(study.get("protocolSection"))

    identification = _safe_dict(
        protocol.get("identificationModule")
    )

    status_module = _safe_dict(
        protocol.get("statusModule")
    )

    design = _safe_dict(
        protocol.get("designModule")
    )

    conditions_module = _safe_dict(
        protocol.get("conditionsModule")
    )

    description_module = _safe_dict(
        protocol.get("descriptionModule")
    )

    nct_id = str(
        identification.get("nctId") or ""
    ).strip()

    title = (
        identification.get("briefTitle")
        or identification.get("officialTitle")
        or nct_id
    )

    phases = _safe_list(design.get("phases"))

    conditions = _safe_list(
        conditions_module.get("conditions")
    )

    status = str(
        status_module.get("overallStatus") or ""
    )

    interventions = _normalize_interventions(study)

    return {
        "source": "ClinicalTrials.gov",
        "evidence_class": "D",
        "verified": True,
        "id": nct_id,
        "nct_id": nct_id,
        "title": title,
        "abstract": (
            description_module.get("briefSummary")
            or description_module.get(
                "detailedDescription"
            )
            or ""
        ),
        "journal": "ClinicalTrials.gov",
        "date": " · ".join(phases),
        "phases": phases,
        "status": status,
        "conditions": conditions,
        "interventions": interventions,
        "url": (
            f"https://clinicaltrials.gov/study/{nct_id}"
            if nct_id
            else ""
        ),
    }


def search_trials_paginated(
    query: str,
    page: int = 1,
    page_size: int = 20,
) -> Dict[str, Any]:
    query = (query or "").strip()

    if not query:
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": page_size,
            "total_pages": 0,
        }

    page = max(1, int(page))
    page_size = max(1, min(int(page_size), 100))

    page_token: Optional[str] = None
    current_page = 1

    while current_page <= page:
        params = {
            "query.term": query,
            "pageSize": page_size,
            "format": "json",
            "countTotal": "true",
        }

        if page_token:
            params["pageToken"] = page_token

        response = requests.get(
            API_URL,
            params=params,
            timeout=TIMEOUT,
        )
        response.raise_for_status()

        payload = response.json()

        studies = payload.get("studies", []) or []
        total = int(payload.get("totalCount", 0) or 0)

        next_token = payload.get("nextPageToken")

        if current_page == page:
            items = [
                normalize_trial(study)
                for study in studies
                if isinstance(study, dict)
            ]

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (
                    (total + page_size - 1) // page_size
                    if total
                    else 0
                ),
                "next_page_token": next_token,
            }

        if not next_token:
            break

        page_token = next_token
        current_page += 1

    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "total_pages": 0,
    }


def search_trials(
    query: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    result = search_trials_paginated(
        query=query,
        page=1,
        page_size=limit,
    )

    return result["items"]