import time
from typing import Any, Dict, List

import requests


EMA_MEDICINES_JSON = (
    "https://www.ema.europa.eu/en/documents/report/"
    "medicines-output-medicines_json-report_en.json"
)

EMA_BASE = "https://www.ema.europa.eu"

CACHE_SECONDS = 6 * 60 * 60
TIMEOUT = 45

_CACHE = {
    "timestamp": 0.0,
    "records": [],
}


def _text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return " · ".join(
            str(item)
            for item in value
            if item is not None
        )

    return str(value).strip()


def _normalize_url(value: str) -> str:
    value = _text(value)

    if not value:
        return ""

    if value.startswith("http://") or value.startswith(
        "https://"
    ):
        return value

    if value.startswith("/"):
        return f"{EMA_BASE}{value}"

    return f"{EMA_BASE}/{value}"


def _extract_records(payload: Any) -> List[dict]:
    if isinstance(payload, list):
        return [
            item
            for item in payload
            if isinstance(item, dict)
        ]

    if not isinstance(payload, dict):
        return []

    for key in [
        "records",
        "data",
        "items",
        "results",
        "medicines",
    ]:
        value = payload.get(key)

        if isinstance(value, list):
            return [
                item
                for item in value
                if isinstance(item, dict)
            ]

    for value in payload.values():
        if isinstance(value, list):
            dict_items = [
                item
                for item in value
                if isinstance(item, dict)
            ]

            if dict_items:
                return dict_items

    return []


def get_ema_records(force_refresh: bool = False) -> List[dict]:
    now = time.time()

    if (
        not force_refresh
        and _CACHE["records"]
        and now - _CACHE["timestamp"] < CACHE_SECONDS
    ):
        return _CACHE["records"]

    response = requests.get(
        EMA_MEDICINES_JSON,
        timeout=TIMEOUT,
        headers={
            "User-Agent": "MSL-ONE/1.0"
        },
    )
    response.raise_for_status()

    payload = response.json()
    records = _extract_records(payload)

    _CACHE["records"] = records
    _CACHE["timestamp"] = now

    return records


def normalize_ema_record(
    record: Dict[str, Any]
) -> Dict[str, Any]:
    name = _text(
        record.get("name_of_medicine")
        or record.get("medicine_name")
        or record.get("name")
    )

    inn = _text(
        record.get(
            "international_non_proprietary_name_common_name"
        )
        or record.get("inn")
    )

    active = _text(
        record.get("active_substance")
    )

    therapeutic_area = _text(
        record.get("therapeutic_area_mesh")
    )

    indication = _text(
        record.get("therapeutic_indication")
    )

    medicine_url = _normalize_url(
        record.get("medicine_url")
    )

    ema_number = _text(
        record.get("ema_product_number")
    )

    status = _text(
        record.get("medicine_status")
        or record.get("opinion_status")
    )

    title_parts = [name]

    if active and active.lower() != name.lower():
        title_parts.append(active)

    title = " — ".join(
        part for part in title_parts if part
    )

    return {
        "source": "EMA",
        "evidence_class": "R1",
        "verified": True,
        "id": ema_number or name,
        "title": title or name or active,
        "name": name,
        "brand_name": name,
        "generic_name": inn or active,
        "active_substance": active,
        "therapeutic_area": therapeutic_area,
        "therapeutic_indication": indication,
        "abstract": indication,
        "journal": "European Medicines Agency",
        "date": _text(
            record.get("last_updated_date")
            or record.get("last_updated")
            or record.get(
                "marketing_authorisation_issued"
            )
        ),
        "status": status,
        "url": medicine_url,
        "medicine_url": medicine_url,
    }


def search_ema_medicines(
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    query = (query or "").strip().lower()

    if not query:
        return []

    records = get_ema_records()

    scored = []

    for record in records:
        normalized = normalize_ema_record(record)

        fields = {
            "name": normalized.get("name", ""),
            "generic": normalized.get(
                "generic_name", ""
            ),
            "active": normalized.get(
                "active_substance", ""
            ),
            "area": normalized.get(
                "therapeutic_area", ""
            ),
            "indication": normalized.get(
                "therapeutic_indication", ""
            ),
        }

        score = 0

        for key, value in fields.items():
            lower = _text(value).lower()

            if not lower:
                continue

            if lower == query:
                score += 100
            elif query in lower:
                if key in {"name", "generic", "active"}:
                    score += 50
                else:
                    score += 8

        if score:
            scored.append((score, normalized))

    scored.sort(
        key=lambda pair: pair[0],
        reverse=True,
    )

    return [
        record
        for _, record in scored[:limit]
    ]


def search_ema(
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    return search_ema_medicines(
        query=query,
        limit=limit,
    )