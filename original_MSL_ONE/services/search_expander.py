from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Iterable, List

from services.ema import search_ema_medicines
from services.fda import (
    normalize_label,
    search_fda_label,
)


STOP_CONTEXT_TERMS = {
    "cancer",
    "carcinoma",
    "tumor",
    "tumour",
    "disease",
    "treatment",
    "therapy",
    "patient",
    "patients",
    "study",
    "trial",
    "phase",
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


def _values(value) -> List[str]:
    if value is None:
        return []

    if isinstance(value, list):
        raw = value
    else:
        raw = [value]

    result = []

    for item in raw:
        text = _text(item).strip()

        if text:
            result.append(text)

    return result


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []

    for value in values:
        clean = _text(value).strip()

        if not clean:
            continue

        key = clean.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(clean)

    return result


def _fda_aliases(asset: str) -> List[str]:
    aliases = []

    try:
        raw_records = search_fda_label(
            asset,
            limit=5,
        )

        for record in raw_records:
            try:
                normalized = normalize_label(record)
            except Exception:
                continue

            for key in [
                "brand_name",
                "generic_name",
                "substance_name",
            ]:
                aliases.extend(
                    _values(
                        normalized.get(key)
                    )
                )

    except Exception:
        pass

    return _dedupe(aliases)


def _ema_aliases(asset: str) -> List[str]:
    aliases = []

    try:
        records = search_ema_medicines(
            asset,
            limit=8,
        )

        for item in records:
            for key in [
                "name",
                "brand_name",
                "generic_name",
                "active_substance",
            ]:
                aliases.extend(
                    _values(
                        item.get(key)
                    )
                )

    except Exception:
        pass

    return _dedupe(aliases)


def resolve_asset_aliases(asset: str) -> List[str]:
    asset = (asset or "").strip()

    if not asset:
        return []

    with ThreadPoolExecutor(
        max_workers=2
    ) as executor:
        fda_future = executor.submit(
            _fda_aliases,
            asset,
        )

        ema_future = executor.submit(
            _ema_aliases,
            asset,
        )

        fda_aliases = fda_future.result()
        ema_aliases = ema_future.result()

    aliases = _dedupe(
        [
            asset,
            *fda_aliases,
            *ema_aliases,
        ]
    )

    # Prevent overly broad garbage aliases
    filtered = []

    asset_lower = asset.lower()

    for alias in aliases:
        alias_lower = alias.lower()

        if len(alias_lower) < 2:
            continue

        if alias_lower in STOP_CONTEXT_TERMS:
            continue

        # Always keep original asset
        if alias_lower == asset_lower:
            filtered.append(alias)
            continue

        # Prefer plausible medicine aliases
        if len(alias.split()) <= 5:
            filtered.append(alias)

    return _dedupe(filtered)[:8]


def _build_pubmed_query(
    aliases: List[str],
    context_terms: List[str],
) -> str:
    if not aliases:
        return " ".join(context_terms)

    alias_queries = []

    for alias in aliases[:6]:
        alias_queries.append(
            f'"{alias}"[Title/Abstract]'
        )

    alias_part = " OR ".join(
        alias_queries
    )

    if len(alias_queries) > 1:
        alias_part = f"({alias_part})"

    if not context_terms:
        return alias_part

    context_queries = []

    for term in context_terms:
        term = term.strip()

        if not term:
            continue

        if " " in term:
            context_queries.append(
                f'"{term}"'
            )
        else:
            context_queries.append(
                term
            )

    if not context_queries:
        return alias_part

    return (
        f"{alias_part} AND "
        + " AND ".join(
            context_queries
        )
    )


def _build_trial_query(
    aliases: List[str],
    context_terms: List[str],
) -> str:
    asset_part = " OR ".join(
        aliases[:5]
    )

    context_part = " ".join(
        context_terms
    )

    if asset_part and context_part:
        return (
            f"({asset_part}) "
            f"{context_part}"
        )

    return asset_part or context_part


def expand_search_query(
    query: str,
) -> Dict[str, Any]:
    raw_query = (query or "").strip()

    if not raw_query:
        return {
            "original_query": "",
            "asset_term": "",
            "aliases": [],
            "context_terms": [],
            "pubmed_query": "",
            "clinicaltrials_query": "",
            "regulatory_terms": [],
            "display_terms": [],
        }

    tokens = raw_query.split()

    asset_term = tokens[0]
    context_terms = tokens[1:]

    aliases = resolve_asset_aliases(
        asset_term
    )

    if not aliases:
        aliases = [asset_term]

    display_terms = _dedupe(
        [
            *aliases,
            *context_terms,
        ]
    )

    return {
        "original_query": raw_query,
        "asset_term": asset_term,
        "aliases": aliases,
        "context_terms": context_terms,
        "pubmed_query": _build_pubmed_query(
            aliases,
            context_terms,
        ),
        "clinicaltrials_query": _build_trial_query(
            aliases,
            context_terms,
        ),
        "regulatory_terms": aliases[:6],
        "display_terms": display_terms[:10],
    }