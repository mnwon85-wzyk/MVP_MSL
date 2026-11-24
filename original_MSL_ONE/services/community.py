from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List
from urllib.parse import quote_plus, urljoin

import requests


REDDIT_BASE = "https://www.reddit.com"

USER_AGENT = (
    "MSL-ONE-Patient-Voice/1.2 "
    "(public RSS medical-intelligence connector)"
)

REQUEST_TIMEOUT = 12

REDDIT_FEED_ITEM_LIMIT = 25
MAX_REDDIT_FEEDS = 4
MAX_PATIENT_SIGNALS = 100


PATIENT_SIGNAL_DISCLAIMER = (
    "Patient Voice signals are derived from self-selected public "
    "online discussions and should not be interpreted as representative "
    "patient evidence or validated RWE. Signals are intended for "
    "hypothesis generation and Medical Affairs exploration only."
)


def _safe_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(value).strip()


def _strip_html(
    value: Any,
) -> str:
    text = _safe_text(value)

    if not text:
        return ""

    text = html.unescape(text)

    text = re.sub(
        r"(?i)<br\s*/?>",
        "\n",
        text,
    )

    text = re.sub(
        r"(?i)</p>",
        "\n",
        text,
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = html.unescape(text)

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n\s*\n+",
        "\n\n",
        text,
    )

    return text.strip()


def _clean_text(
    value: Any,
    max_length: int = 5000,
) -> str:
    text = _strip_html(value)

    if not text:
        return ""

    if len(text) > max_length:
        return (
            text[:max_length].rstrip()
            + "…"
        )

    return text


def _normalize_reddit_url(
    value: str,
) -> str:
    url = _safe_text(value)

    if not url:
        return ""

    if url.startswith("/"):
        return urljoin(
            REDDIT_BASE,
            url,
        )

    return url


def _parse_date(
    value: str,
) -> str:
    value = _safe_text(value)

    if not value:
        return ""

    try:
        parsed = (
            datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )
        )

        return parsed.isoformat(
            timespec="seconds"
        )

    except Exception:
        return value


def _date_sort_value(
    item: Dict[str, Any],
) -> float:
    value = _safe_text(
        item.get("created_at")
        or item.get("date")
    )

    if not value:
        return 0.0

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

        return parsed.timestamp()

    except Exception:
        return 0.0


def _dedupe_items(
    items: List[
        Dict[str, Any]
    ],
) -> List[
    Dict[str, Any]
]:
    result = []
    seen = set()

    for item in items:
        key = (
            _safe_text(
                item.get("url")
                or item.get("id")
                or item.get("title")
            )
            .lower()
        )

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def _recommended_subreddits(
    query: str,
) -> List[str]:
    q = (
        query or ""
    ).lower()

    communities = []

    mappings = [
        (
            [
                "lung cancer",
                "lungcancer",
                "nsclc",
                "egfr",
                "alk",
                "ros1",
                "osimertinib",
                "tagrisso",
                "afatinib",
                "gilotrif",
                "giotrif",
            ],
            [
                "lungcancer",
                "cancer",
            ],
        ),

        (
            [
                "breast cancer",
                "breastcancer",
                "her2",
                "trastuzumab",
                "enhertu",
            ],
            [
                "breastcancer",
                "cancer",
            ],
        ),

        (
            [
                "myeloma",
                "multiple myeloma",
                "blenrep",
            ],
            [
                "MultipleMyeloma",
                "cancer",
            ],
        ),

        (
            [
                "endometrial",
                "ovarian",
                "cervical",
                "jemperli",
                "dostarlimab",
                "zejula",
            ],
            [
                "cancer",
                "ovariancancer",
            ],
        ),

        (
            [
                "cancer",
                "chemotherapy",
                "immunotherapy",
                "keytruda",
                "pembrolizumab",
            ],
            [
                "cancer",
            ],
        ),

        (
            [
                "wegovy",
                "semaglutide",
                "ozempic",
                "obesity",
                "weight loss",
            ],
            [
                "WegovyWeightLoss",
                "Semaglutide",
                "loseit",
            ],
        ),

        (
            [
                "mounjaro",
                "zepbound",
                "tirzepatide",
            ],
            [
                "Mounjaro",
                "Zepbound",
                "loseit",
            ],
        ),

        (
            [
                "diabetes",
                "type 2 diabetes",
                "t2d",
            ],
            [
                "diabetes",
                "diabetes_t2",
            ],
        ),
    ]

    for keywords, subreddits in mappings:
        if any(
            keyword in q
            for keyword in keywords
        ):
            communities.extend(
                subreddits
            )

    unique = []

    for community in communities:
        if (
            community
            not in unique
        ):
            unique.append(
                community
            )

    if "all" not in unique:
        unique.append("all")

    return unique[
        :MAX_REDDIT_FEEDS
    ]


def _build_reddit_search_feed(
    subreddit: str,
    query: str,
    sort: str = "new",
) -> str:
    encoded_query = (
        quote_plus(query)
    )

    if (
        subreddit.lower()
        == "all"
    ):
        return (
            f"{REDDIT_BASE}/search.rss"
            f"?q={encoded_query}"
            f"&sort={sort}"
        )

    return (
        f"{REDDIT_BASE}/r/{subreddit}"
        f"/search.rss"
        f"?q={encoded_query}"
        f"&restrict_sr=on"
        f"&sort={sort}"
    )


def _request_feed(
    url: str,
) -> requests.Response:
    headers = {
        "User-Agent":
            USER_AGENT,

        "Accept":
            (
                "application/atom+xml,"
                "application/rss+xml,"
                "application/xml,"
                "text/xml;q=0.9,"
                "*/*;q=0.8"
            ),

        "Accept-Language":
            "en-US,en;q=0.9",
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=REQUEST_TIMEOUT,
        allow_redirects=True,
    )

    response.raise_for_status()

    return response


def _atom_text(
    entry: ET.Element,
    name: str,
) -> str:
    for child in entry:
        local_name = (
            child.tag.split("}")[-1]
        )

        if local_name == name:
            return (
                child.text or ""
            ).strip()

    return ""


def _atom_link(
    entry: ET.Element,
) -> str:
    for child in entry:
        local_name = (
            child.tag.split("}")[-1]
        )

        if local_name != "link":
            continue

        href = (
            child.attrib.get(
                "href",
                "",
            )
        )

        if href:
            return (
                _normalize_reddit_url(
                    href
                )
            )

    return ""


def _extract_subreddit_from_url(
    url: str,
) -> str:
    match = re.search(
        r"/r/([^/]+)/",
        url,
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    return match.group(1)


def _parse_atom_feed(
    xml_text: str,
    limit: int = (
        REDDIT_FEED_ITEM_LIMIT
    ),
) -> List[
    Dict[str, Any]
]:
    root = ET.fromstring(
        xml_text
    )

    entries = []

    for element in root.iter():
        if (
            element.tag
            .split("}")[-1]
            == "entry"
        ):
            entries.append(
                element
            )

    items = []

    safe_limit = max(
        1,
        min(
            int(limit),
            REDDIT_FEED_ITEM_LIMIT,
        ),
    )

    for entry in entries:
        title = _clean_text(
            _atom_text(
                entry,
                "title",
            ),
            max_length=700,
        )

        entry_id = _safe_text(
            _atom_text(
                entry,
                "id",
            )
        )

        published = (
            _atom_text(
                entry,
                "published",
            )
            or
            _atom_text(
                entry,
                "updated",
            )
        )

        content = (
            _atom_text(
                entry,
                "content",
            )
            or
            _atom_text(
                entry,
                "summary",
            )
        )

        body = _clean_text(
            content,
            max_length=5000,
        )

        url = _atom_link(
            entry
        )

        subreddit = (
            _extract_subreddit_from_url(
                url
            )
        )

        text_parts = []

        if title:
            text_parts.append(
                title
            )

        if body:
            text_parts.append(
                body
            )

        combined_text = (
            "\n\n".join(
                text_parts
            )
        )

        if (
            not title
            and not body
        ):
            continue

        items.append(
            {
                "source":
                    "Reddit RSS",

                "source_type":
                    "PUBLIC COMMUNITY",

                "signal_class":
                    "PATIENT SIGNAL",

                "evidence_status":
                    "PATIENT SIGNAL",

                "id":
                    (
                        entry_id
                        or url
                        or title
                    ),

                "title":
                    (
                        title
                        or
                        "Reddit discussion"
                    ),

                "text":
                    combined_text,

                "body":
                    body,

                "url":
                    url,

                "subreddit":
                    subreddit,

                "created_at":
                    _parse_date(
                        published
                    ),

                "date":
                    _parse_date(
                        published
                    ),

                "verified":
                    False,

                "representative":
                    False,

                "rwe":
                    False,

                "collection_method":
                    "PUBLIC RSS",
            }
        )

        if (
            len(items)
            >= safe_limit
        ):
            break

    return items


def _collect_reddit_feed(
    subreddit: str,
    query: str,
) -> Dict[str, Any]:
    feed_url = (
        _build_reddit_search_feed(
            subreddit=subreddit,
            query=query,
            sort="new",
        )
    )

    try:
        response = (
            _request_feed(
                feed_url
            )
        )

        items = (
            _parse_atom_feed(
                response.text,
                limit=
                    REDDIT_FEED_ITEM_LIMIT,
            )
        )

        return {
            "subreddit":
                subreddit,

            "url":
                feed_url,

            "status":
                "ok",

            "message":
                "",

            "items":
                items,
        }

    except requests.HTTPError as exc:
        code = (
            exc.response.status_code
            if exc.response
            is not None
            else "unknown"
        )

        return {
            "subreddit":
                subreddit,

            "url":
                feed_url,

            "status":
                "error",

            "message":
                f"HTTP {code}",

            "items":
                [],
        }

    except requests.RequestException as exc:
        return {
            "subreddit":
                subreddit,

            "url":
                feed_url,

            "status":
                "error",

            "message":
                type(exc).__name__,

            "items":
                [],
        }

    except ET.ParseError:
        return {
            "subreddit":
                subreddit,

            "url":
                feed_url,

            "status":
                "error",

            "message":
                "RSS XML parse error",

            "items":
                [],
        }

    except Exception as exc:
        return {
            "subreddit":
                subreddit,

            "url":
                feed_url,

            "status":
                "error",

            "message":
                type(exc).__name__,

            "items":
                [],
        }


def search_reddit_rss(
    query: str,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Best-effort public Reddit RSS aggregation.

    Public RSS does not provide a reliable
    Reddit Data API-style 'after' cursor.

    Therefore MSL ONE fans out to up to
    four relevant public RSS feeds,
    collects up to 25 entries from each,
    deduplicates globally, sorts newest first,
    and returns up to 100 unique signals.
    """

    query = (
        query or ""
    ).strip()

    if not query:
        return {
            "items":
                [],

            "total":
                0,

            "status":
                "empty_query",

            "message":
                "Query is empty.",

            "feeds_checked":
                [],
        }

    safe_limit = max(
        1,
        min(
            int(limit),
            MAX_PATIENT_SIGNALS,
        ),
    )

    subreddits = (
        _recommended_subreddits(
            query
        )
    )

    all_items = []
    feed_results = []

    workers = max(
        1,
        min(
            MAX_REDDIT_FEEDS,
            len(subreddits),
        ),
    )

    with ThreadPoolExecutor(
        max_workers=workers
    ) as executor:

        futures = [
            executor.submit(
                _collect_reddit_feed,
                subreddit,
                query,
            )
            for subreddit
            in subreddits
        ]

        for future in futures:
            feed_results.append(
                future.result()
            )

    for result in feed_results:
        all_items.extend(
            result.get(
                "items",
                [],
            )
        )

    all_items = (
        _dedupe_items(
            all_items
        )
    )

    all_items = sorted(
        all_items,
        key=_date_sort_value,
        reverse=True,
    )

    all_items = (
        all_items[
            :safe_limit
        ]
    )

    successful_feeds = [
        result
        for result
        in feed_results
        if (
            result.get("status")
            == "ok"
        )
    ]

    failed_feeds = [
        result
        for result
        in feed_results
        if (
            result.get("status")
            != "ok"
        )
    ]

    if all_items:
        status = "ok"

        message = (
            f"{len(all_items)} unique public Reddit RSS "
            f"signals collected from "
            f"{len(successful_feeds)} feed(s)."
        )

        if failed_feeds:
            message += (
                " Some feeds were unavailable."
            )

    elif failed_feeds:
        status = "unavailable"

        message = (
            "Reddit RSS returned no usable signals."
        )

    else:
        status = "no_results"

        message = (
            "Reddit RSS was reachable but returned "
            "no matching public posts."
        )

    return {
        "items":
            all_items,

        "total":
            len(all_items),

        "status":
            status,

        "message":
            message,

        "feeds_checked":
            [
                {
                    "subreddit":
                        result[
                            "subreddit"
                        ],

                    "url":
                        result[
                            "url"
                        ],

                    "status":
                        result[
                            "status"
                        ],

                    "count":
                        len(
                            result.get(
                                "items",
                                [],
                            )
                        ),

                    "message":
                        result.get(
                            "message",
                            "",
                        ),
                }
                for result
                in feed_results
            ],
    }


def search_dcinside(
    query: str,
    limit: int = 20,
) -> Dict[str, Any]:
    return {
        "items":
            [],

        "status":
            "not_connected",

        "message":
            (
                "DCInside connector is not enabled. "
                "No synthetic DCInside signals were generated."
            ),
    }


def search_patient_voice(
    query: str,
    sources=None,
    limit: int = 100,
) -> Dict[str, Any]:

    query = (
        query or ""
    ).strip()

    if not query:
        return {
            "query":
                "",

            "items":
                [],

            "count":
                0,

            "total":
                0,

            "source_status":
                {},

            "source_messages":
                {},

            "source_details":
                {},

            "disclaimer":
                PATIENT_SIGNAL_DISCLAIMER,
        }

    if sources:
        requested = {
            str(source)
            .strip()
            .lower()
            for source
            in sources
        }

    else:
        requested = {
            "reddit",
        }

    items = []

    source_status = {}
    source_messages = {}
    source_details = {}

    reddit_requested = any(
        source in requested
        for source in {
            "reddit",
            "reddit rss",
            "rss",
        }
    )

    if reddit_requested:
        reddit_result = (
            search_reddit_rss(
                query=query,
                limit=limit,
            )
        )

        items.extend(
            reddit_result.get(
                "items",
                [],
            )
        )

        source_status[
            "Reddit"
        ] = (
            reddit_result.get(
                "status",
                "unknown",
            )
        )

        source_messages[
            "Reddit"
        ] = (
            reddit_result.get(
                "message",
                "",
            )
        )

        source_details[
            "Reddit"
        ] = (
            reddit_result.get(
                "feeds_checked",
                [],
            )
        )

    dc_requested = any(
        source in requested
        for source in {
            "dcinside",
            "dc",
            "디시",
            "디시인사이드",
        }
    )

    if dc_requested:
        dc_result = (
            search_dcinside(
                query=query,
                limit=limit,
            )
        )

        items.extend(
            dc_result.get(
                "items",
                [],
            )
        )

        source_status[
            "DCInside"
        ] = (
            dc_result.get(
                "status",
                "unknown",
            )
        )

        source_messages[
            "DCInside"
        ] = (
            dc_result.get(
                "message",
                "",
            )
        )

    items = (
        _dedupe_items(
            items
        )
    )

    items = sorted(
        items,
        key=_date_sort_value,
        reverse=True,
    )

    items = items[
        :MAX_PATIENT_SIGNALS
    ]

    return {
        "query":
            query,

        "items":
            items,

        "count":
            len(items),

        "total":
            len(items),

        "source_status":
            source_status,

        "source_messages":
            source_messages,

        "source_details":
            source_details,

        "disclaimer":
            PATIENT_SIGNAL_DISCLAIMER,
    }