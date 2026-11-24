import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

from services.clinicaltrials import (
    search_trials_paginated,
)
from services.ema import search_ema_medicines
from services.fda import (
    fda_drugs_page,
    normalize_label,
    search_fda_label,
)
from services.search_expander import (
    resolve_asset_aliases,
)


COMMON_DISEASE_EXPANSIONS = {
    "nsclc": [
        "nsclc",
        "non-small cell lung cancer",
        "non small cell lung cancer",
    ],
    "sclc": [
        "sclc",
        "small cell lung cancer",
    ],
    "hcc": [
        "hcc",
        "hepatocellular carcinoma",
    ],
    "rcc": [
        "rcc",
        "renal cell carcinoma",
    ],
    "crc": [
        "crc",
        "colorectal cancer",
    ],
    "tnbc": [
        "tnbc",
        "triple-negative breast cancer",
        "triple negative breast cancer",
    ],
    "obesity": [
        "obesity",
        "weight management",
        "overweight",
    ],
    "endometrial": [
        "endometrial cancer",
        "endometrial carcinoma",
    ],
}


SKIP_INTERVENTIONS = {
    "placebo",
    "standard of care",
    "standard care",
    "best supportive care",
    "usual care",
    "observation",
    "no intervention",
    "lifestyle intervention",
    "diet",
    "exercise",
}


def _text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            str(item)
            for item in value
            if item is not None
        )

    return str(value).strip()


def _clean_intervention_name(
    value: str,
) -> str:
    value = _text(value)

    value = re.sub(
        r"\([^)]*\)",
        " ",
        value,
    )

    value = re.sub(
        r"\b\d+(\.\d+)?\s*(mg|mcg|µg|g|ml)\b",
        " ",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"\b(tablet|capsule|injection|oral|"
        r"subcutaneous|intravenous|solution|dose)\b",
        " ",
        value,
        flags=re.I,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    ).strip(" ,-+")

    return value


def _normalize_key(value: str) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "",
        _text(value).lower(),
    )


def _disease_terms(
    disease: str,
) -> List[str]:
    disease_lower = disease.lower()

    terms = [disease_lower]

    for key, expansions in (
        COMMON_DISEASE_EXPANSIONS.items()
    ):
        if key in disease_lower:
            terms.extend(expansions)

    words = re.findall(
        r"[a-zA-Z][a-zA-Z-]{3,}",
        disease_lower,
    )

    terms.extend(words)

    seen = set()
    result = []

    for term in terms:
        clean = term.strip().lower()

        if not clean or clean in seen:
            continue

        seen.add(clean)
        result.append(clean)

    return result


def _indication_matches(
    text: str,
    disease: str,
) -> bool:
    haystack = _text(text).lower()

    if not haystack:
        return False

    for term in _disease_terms(disease):
        if term in haystack:
            return True

    return False


def _phase_rank(phases: List[str]) -> int:
    text = " ".join(phases).upper()

    if "PHASE4" in text or "PHASE 4" in text:
        return 4

    if "PHASE3" in text or "PHASE 3" in text:
        return 3

    if "PHASE2" in text or "PHASE 2" in text:
        return 2

    if "PHASE1" in text or "PHASE 1" in text:
        return 1

    return 0


def _regulatory_profile(
    drug_name: str,
    disease: str,
) -> Dict[str, Any]:
    fda_records = []
    ema_records = []

    try:
        raw_fda = search_fda_label(
            drug_name,
            limit=5,
        )

        for raw in raw_fda:
            try:
                normalized = normalize_label(
                    raw
                )

                application = _text(
                    normalized.get(
                        "application_number"
                    )
                )

                exact_url = (
                    fda_drugs_page(application)
                    if application
                    else normalized.get(
                        "source_url", ""
                    )
                )

                normalized["url"] = exact_url
                fda_records.append(
                    normalized
                )

            except Exception:
                continue

    except Exception:
        pass

    try:
        ema_records = search_ema_medicines(
            drug_name,
            limit=5,
        )

    except Exception:
        ema_records = []

    matched_fda = []

    for item in fda_records:
        indication = _text(
            item.get("indications")
        )

        if _indication_matches(
            indication,
            disease,
        ):
            matched_fda.append(item)

    matched_ema = []

    for item in ema_records:
        indication_text = " ".join(
            [
                _text(
                    item.get(
                        "therapeutic_indication"
                    )
                ),
                _text(
                    item.get(
                        "therapeutic_area"
                    )
                ),
            ]
        )

        if _indication_matches(
            indication_text,
            disease,
        ):
            matched_ema.append(item)

    brands = set()

    for item in (
        fda_records + ema_records
    ):
        for key in [
            "brand_name",
            "name",
        ]:
            value = _text(
                item.get(key)
            )

            if value:
                brands.add(value)

    approved_match = bool(
        matched_fda or matched_ema
    )

    if approved_match:
        status = (
            "Regulatory indication match"
        )

    elif fda_records or ema_records:
        status = (
            "Regulatory record found — "
            "indication check required"
        )

    else:
        status = (
            "No verified regulatory match"
        )

    sources = []

    for item in (
        matched_fda
        + matched_ema
        + fda_records[:1]
        + ema_records[:1]
    ):
        url = _text(
            item.get("url")
            or item.get("medicine_url")
            or item.get("source_url")
        )

        if not url:
            continue

        source_name = _text(
            item.get("source")
        )

        source_item = {
            "source": source_name,
            "title": _text(
                item.get("title")
                or item.get("brand_name")
                or drug_name
            ),
            "url": url,
        }

        if source_item not in sources:
            sources.append(source_item)

    return {
        "approved_for_context": approved_match,
        "regulatory_status": status,
        "brands": sorted(brands),
        "sources": sources[:4],
    }


def _discover_interventions(
    disease: str,
    setting: str = "",
    biomarker: str = "",
) -> Dict[str, Any]:
    query = " ".join(
        value.strip()
        for value in [
            disease,
            setting,
            biomarker,
        ]
        if value and value.strip()
    )

    result = search_trials_paginated(
        query=query,
        page=1,
        page_size=100,
    )

    grouped = defaultdict(
        lambda: {
            "display_name": "",
            "trial_count": 0,
            "phases": set(),
            "statuses": set(),
            "trial_sources": [],
        }
    )

    for trial in result["items"]:
        phases = trial.get(
            "phases", []
        ) or []

        status = _text(
            trial.get("status")
        )

        for intervention in (
            trial.get(
                "interventions", []
            )
            or []
        ):
            intervention_type = _text(
                intervention.get("type")
            ).upper()

            if intervention_type not in {
                "DRUG",
                "BIOLOGICAL",
            }:
                continue

            name = _clean_intervention_name(
                intervention.get("name")
            )

            if not name:
                continue

            if name.lower() in SKIP_INTERVENTIONS:
                continue

            key = _normalize_key(name)

            if len(key) < 3:
                continue

            item = grouped[key]

            if not item["display_name"]:
                item["display_name"] = name

            item["trial_count"] += 1

            for phase in phases:
                item["phases"].add(
                    _text(phase)
                )

            if status:
                item["statuses"].add(
                    status
                )

            if len(
                item["trial_sources"]
            ) < 4:
                item[
                    "trial_sources"
                ].append(
                    {
                        "source": (
                            "ClinicalTrials.gov"
                        ),
                        "id": trial.get("id"),
                        "title": trial.get(
                            "title"
                        ),
                        "url": trial.get(
                            "url"
                        ),
                    }
                )

    candidates = []

    for item in grouped.values():
        phases = sorted(
            item["phases"]
        )

        candidates.append(
            {
                "name": item[
                    "display_name"
                ],
                "trial_count": item[
                    "trial_count"
                ],
                "phases": phases,
                "phase_rank": (
                    _phase_rank(phases)
                ),
                "statuses": sorted(
                    item["statuses"]
                ),
                "trial_sources": item[
                    "trial_sources"
                ],
            }
        )

    candidates.sort(
        key=lambda item: (
            item["phase_rank"],
            item["trial_count"],
        ),
        reverse=True,
    )

    return {
        "query": query,
        "trial_total": result["total"],
        "candidates": candidates,
    }


def build_treatment_landscape(
    disease: str,
    asset: str = "",
    setting: str = "",
    biomarker: str = "",
) -> Dict[str, Any]:
    disease = (disease or "").strip()
    asset = (asset or "").strip()

    if not disease:
        raise ValueError(
            "Disease / indication is required."
        )

    asset_aliases = (
        resolve_asset_aliases(asset)
        if asset
        else []
    )

    own_keys = {
        _normalize_key(alias)
        for alias in asset_aliases
        if alias
    }

    discovery = _discover_interventions(
        disease=disease,
        setting=setting,
        biomarker=biomarker,
    )

    candidates = []

    for candidate in (
        discovery["candidates"]
    ):
        key = _normalize_key(
            candidate["name"]
        )

        if key in own_keys:
            continue

        if any(
            own_key
            and (
                own_key in key
                or key in own_key
            )
            for own_key in own_keys
        ):
            continue

        candidates.append(candidate)

        if len(candidates) >= 8:
            break

    with ThreadPoolExecutor(
        max_workers=5
    ) as executor:
        future_map = {
            executor.submit(
                _regulatory_profile,
                candidate["name"],
                disease,
            ): candidate
            for candidate in candidates
        }

        competitors = []

        for future, candidate in (
            future_map.items()
        ):
            try:
                regulatory = (
                    future.result()
                )
            except Exception:
                regulatory = {
                    "approved_for_context": False,
                    "regulatory_status": (
                        "Regulatory check failed"
                    ),
                    "brands": [],
                    "sources": [],
                }

            competitors.append(
                {
                    **candidate,
                    **regulatory,
                    "role": "Competitor",
                }
            )

    competitors.sort(
        key=lambda item: (
            bool(
                item.get(
                    "approved_for_context"
                )
            ),
            item.get(
                "phase_rank", 0
            ),
            item.get(
                "trial_count", 0
            ),
        ),
        reverse=True,
    )

    own_asset = None

    if asset:
        regulatory = _regulatory_profile(
            asset,
            disease,
        )

        own_trials = []

        for trial_candidate in (
            discovery["candidates"]
        ):
            key = _normalize_key(
                trial_candidate["name"]
            )

            if key in own_keys or any(
                own_key
                and (
                    own_key in key
                    or key in own_key
                )
                for own_key in own_keys
            ):
                own_trials.append(
                    trial_candidate
                )

        own_asset = {
            "name": asset,
            "aliases": asset_aliases,
            "role": "My asset",
            "trial_count": sum(
                item["trial_count"]
                for item in own_trials
            ),
            "phases": sorted(
                {
                    phase
                    for item in own_trials
                    for phase in (
                        item.get(
                            "phases", []
                        )
                    )
                }
            ),
            **regulatory,
        }

    approved_competitors = [
        item
        for item in competitors
        if item.get(
            "approved_for_context"
        )
    ]

    emerging_competitors = [
        item
        for item in competitors
        if not item.get(
            "approved_for_context"
        )
    ]

    changing = []

    phase3_count = sum(
        1
        for item in competitors
        if item.get(
            "phase_rank", 0
        ) >= 3
    )

    if phase3_count:
        changing.append(
            {
                "signal": (
                    f"{phase3_count} discovered "
                    "competitor intervention(s) "
                    "have Phase III or later "
                    "development activity."
                ),
                "basis": (
                    "ClinicalTrials.gov"
                ),
            }
        )

    if approved_competitors:
        changing.append(
            {
                "signal": (
                    f"{len(approved_competitors)} "
                    "discovered competitor(s) "
                    "have a regulatory indication "
                    "match for the entered disease "
                    "context."
                ),
                "basis": "FDA / EMA",
            }
        )

    return {
        "disease": disease,
        "asset": asset,
        "setting": setting,
        "biomarker": biomarker,
        "discovery_query": (
            discovery["query"]
        ),
        "trial_total": (
            discovery["trial_total"]
        ),
        "own_asset": own_asset,
        "competitors": competitors,
        "approved_competitors": (
            approved_competitors
        ),
        "emerging_competitors": (
            emerging_competitors
        ),
        "what_is_changing": changing,
        "method": (
            "Disease/setting/biomarker → "
            "ClinicalTrials.gov intervention "
            "discovery → drug normalization → "
            "FDA/EMA indication verification"
        ),
        "warning": (
            "Regulatory records and trial "
            "activity are source signals, not "
            "treatment recommendations. "
            "Investigational therapies must not "
            "be presented as approved treatment."
        ),
    }