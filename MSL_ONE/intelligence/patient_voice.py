from __future__ import annotations

import re

from collections import Counter
from typing import Any


PATIENT_VOICE_DISCLAIMER = (
    "Patient Voice signals are derived from self-selected "
    "public online discussions and should not be interpreted "
    "as representative patient evidence or validated RWE. "
    "Signals are intended for hypothesis generation and "
    "Medical Affairs exploration only."
)


THEME_KEYWORDS = {
    "부작용 / Side Effects": [
        "부작용",
        "통증",
        "피로",
        "구토",
        "메스꺼움",
        "설사",
        "변비",
        "발진",
        "가려움",
        "탈모",
        "어지러움",
        "두통",
        "식욕",
        "체중",
        "혈당",
        "호흡곤란",
        "숨참",
        "감염",
        "열",
        "발열",
        "빈혈",
        "혈소판",
        "백혈구",
        "신경병증",

        "side effect",
        "side effects",
        "adverse event",
        "toxicity",
        "fatigue",
        "nausea",
        "vomiting",
        "diarrhea",
        "constipation",
        "rash",
        "itching",
        "alopecia",
        "dizziness",
        "headache",
        "neuropathy",
        "infection",
        "fever",
        "anemia",
        "thrombocytopenia",
        "dyspnea",
    ],

    "치료 지속·중단 / Continuation": [
        "중단",
        "치료 중단",
        "약 중단",
        "복용 중단",
        "계속 치료",
        "계속 복용",
        "치료 지속",
        "용량 감소",
        "용량 조절",
        "휴약",
        "재투여",

        "discontinue",
        "discontinuation",
        "stopped treatment",
        "stop treatment",
        "continue treatment",
        "dose reduction",
        "dose modification",
        "dose interruption",
        "treatment interruption",
        "rechallenge",
    ],

    "삶의 질 / Quality of Life": [
        "삶의 질",
        "일상생활",
        "일상 생활",
        "직장",
        "출근",
        "잠",
        "수면",
        "식사",
        "운동",
        "생활",
        "가족",
        "돌봄",
        "보호자",

        "quality of life",
        "qol",
        "daily life",
        "daily activity",
        "work",
        "sleep",
        "caregiver",
        "functional",
        "functioning",
    ],

    "치료 효과 기대 / Treatment Expectations": [
        "효과",
        "반응",
        "호전",
        "좋아졌",
        "줄어들",
        "종양 감소",
        "완치",
        "재발",
        "진행",
        "생존",
        "얼마나 듣",
        "효과 있",

        "response",
        "respond",
        "effective",
        "efficacy",
        "tumor shrink",
        "tumour shrink",
        "progression",
        "survival",
        "recurrence",
        "remission",
    ],

    "바이오마커 / Biomarker": [
        "바이오마커",
        "검사",
        "유전자 검사",
        "유전자검사",
        "조직검사",

        "pd-l1",
        "pdl1",
        "egfr",
        "alk",
        "ros1",
        "kras",
        "her2",
        "msi",
        "msi-h",
        "dmmr",
        "brca",

        "biomarker",
        "genetic test",
        "genomic",
        "mutation",
        "testing",
    ],

    "치료 순서 / Sequencing": [
        "1차 치료",
        "2차 치료",
        "3차 치료",
        "일차 치료",
        "이차 치료",
        "삼차 치료",
        "다음 치료",
        "다음 약",
        "치료 순서",
        "병용",
        "단독",

        "first line",
        "first-line",
        "second line",
        "second-line",
        "third line",
        "third-line",
        "next treatment",
        "sequence",
        "sequencing",
        "combination",
        "monotherapy",
    ],

    "비용·접근성 / Access": [
        "비용",
        "가격",
        "보험",
        "급여",
        "비급여",
        "약값",
        "병원비",
        "지원",
        "접근",
        "처방",
        "구할 수",

        "cost",
        "price",
        "insurance",
        "coverage",
        "reimbursement",
        "access",
        "availability",
        "afford",
    ],

    "정보 부족 / Information Gap": [
        "모르겠",
        "궁금",
        "정보",
        "찾아봐도",
        "알 수 없",
        "설명",
        "질문",
        "어떻게",
        "왜",
        "어떤",
        "차이",

        "meaning",
        "don't know",
        "do not know",
        "not sure",
        "question",
        "information",
        "explain",
        "difference",
        "what does",
        "how do",
        "why does",
    ],
}


THEME_ORDER = list(
    THEME_KEYWORDS.keys()
)


REPRESENTATIVE_SIGNAL_LIMIT = 16
REPRESENTATIVE_PER_THEME = 2
REPRESENTATIVE_TEXT_LIMIT = 1200


def _safe_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return value.strip()

    if isinstance(
        value,
        (int, float, bool),
    ):
        return str(value)

    if isinstance(
        value,
        list,
    ):
        return " ".join(
            _safe_text(item)
            for item in value
            if item is not None
        ).strip()

    if isinstance(
        value,
        dict,
    ):
        return " ".join(
            _safe_text(item)
            for item
            in value.values()
            if item is not None
        ).strip()

    return str(value).strip()


def _normalize_text(
    value: Any,
) -> str:
    text = (
        _safe_text(value)
        .lower()
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def classify_text(
    text: str,
) -> dict[str, Any]:

    normalized = (
        _normalize_text(
            text
        )
    )

    if not normalized:
        return {
            "primary_theme":
                "기타 / Other",

            "themes":
                [
                    "기타 / Other"
                ],

            "scores":
                {},
        }

    scores = {}

    for theme, keywords in (
        THEME_KEYWORDS.items()
    ):
        score = 0

        for keyword in keywords:
            if (
                keyword.lower()
                in normalized
            ):
                score += 1

        if score > 0:
            scores[
                theme
            ] = score

    if not scores:
        return {
            "primary_theme":
                "기타 / Other",

            "themes":
                [
                    "기타 / Other"
                ],

            "scores":
                {},
        }

    ranked = sorted(
        scores.items(),
        key=lambda item: (
            -item[1],
            (
                THEME_ORDER.index(
                    item[0]
                )
                if item[0]
                in THEME_ORDER
                else 999
            ),
        ),
    )

    themes = [
        theme
        for theme, _score
        in ranked
    ]

    return {
        "primary_theme":
            themes[0],

        "themes":
            themes,

        "scores":
            scores,
    }


def _normalize_item(
    item: dict[str, Any],
) -> dict[str, Any]:

    title = _safe_text(
        item.get("title")
    )

    body = _safe_text(
        item.get("text")
        or item.get("description")
        or item.get("body")
        or item.get("content")
        or item.get("snippet")
    )

    combined_text = (
        f"{title} {body}"
    ).strip()

    classification = (
        classify_text(
            combined_text
        )
    )

    return {
        **item,

        "title":
            title,

        "text":
            body,

        "primary_theme":
            classification[
                "primary_theme"
            ],

        "theme":
            classification[
                "primary_theme"
            ],

        "themes":
            classification[
                "themes"
            ],

        "theme_scores":
            classification[
                "scores"
            ],

        "signal_class":
            "PATIENT SIGNAL",

        "evidence_status":
            "PATIENT SIGNAL",

        "representative":
            False,

        "rwe":
            False,
    }


def select_representative_signals(
    items: list[
        dict[str, Any]
    ],
    max_items: int = (
        REPRESENTATIVE_SIGNAL_LIMIT
    ),
    per_theme: int = (
        REPRESENTATIVE_PER_THEME
    ),
) -> list[
    dict[str, Any]
]:
    """
    Representative sampling is deterministic.

    1. Highest-frequency themes first.
    2. Up to N signals per theme.
    3. Prefer signals with stronger keyword/theme scores.
    4. Fill remaining slots with unused signals.
    """

    if not items:
        return []

    theme_counter = Counter(
        item.get(
            "primary_theme",
            "기타 / Other",
        )
        for item in items
    )

    theme_order = [
        theme
        for theme, _count
        in theme_counter.most_common()
    ]

    chosen = []
    chosen_keys = set()

    def key_for(
        item: dict[str, Any],
    ) -> str:
        return _safe_text(
            item.get("url")
            or item.get("id")
            or item.get("title")
        )

    for theme in theme_order:
        candidates = [
            item
            for item in items
            if (
                item.get(
                    "primary_theme"
                )
                == theme
            )
        ]

        candidates = sorted(
            candidates,
            key=lambda item: (
                -int(
                    (
                        item.get(
                            "theme_scores",
                            {},
                        )
                        or {}
                    ).get(
                        theme,
                        0,
                    )
                ),
                -len(
                    _safe_text(
                        item.get("text")
                    )
                ),
            ),
        )

        theme_count = 0

        for item in candidates:
            key = key_for(item)

            if not key:
                continue

            if key in chosen_keys:
                continue

            selected = {
                **item,
                "representative":
                    True,
            }

            chosen.append(
                selected
            )

            chosen_keys.add(
                key
            )

            theme_count += 1

            if (
                theme_count
                >= per_theme
            ):
                break

            if (
                len(chosen)
                >= max_items
            ):
                return chosen

    for item in items:
        if (
            len(chosen)
            >= max_items
        ):
            break

        key = key_for(item)

        if (
            not key
            or key in chosen_keys
        ):
            continue

        chosen.append(
            {
                **item,
                "representative":
                    True,
            }
        )

        chosen_keys.add(
            key
        )

    return chosen


def build_patient_voice_context(
    items: list[
        dict[str, Any]
    ],
    max_items: int = (
        REPRESENTATIVE_SIGNAL_LIMIT
    ),
    max_chars_per_item: int = (
        REPRESENTATIVE_TEXT_LIMIT
    ),
) -> str:

    sections = []

    for index, item in enumerate(
        items[:max_items],
        start=1,
    ):
        title = _safe_text(
            item.get("title")
        )

        source = _safe_text(
            item.get("source")
            or item.get("provider")
            or "Public community"
        )

        url = _safe_text(
            item.get("url")
        )

        date = _safe_text(
            item.get("date")
            or item.get(
                "created_at"
            )
        )

        subreddit = _safe_text(
            item.get("subreddit")
        )

        theme = _safe_text(
            item.get(
                "primary_theme"
            )
            or item.get("theme")
        )

        text = _safe_text(
            item.get("text")
            or item.get("body")
        )

        text = text[
            :max_chars_per_item
        ]

        sections.append(
            f"[SIGNAL {index}]\n"
            f"Source: {source}\n"
            f"Community: {subreddit}\n"
            f"Date: {date}\n"
            f"Rule-based theme: {theme}\n"
            f"Title: {title}\n"
            f"URL: {url}\n"
            f"Public discussion excerpt:\n"
            f"{text}"
        )

    return "\n\n".join(
        sections
    )


def analyze_patient_voice(
    items: list[
        dict[str, Any]
    ] | None,
) -> dict[str, Any]:

    if not items:
        return {
            "items":
                [],

            "total_items":
                0,

            "theme_summary":
                [],

            "top_themes":
                [],

            "source_summary":
                [],

            "representative_items":
                [],

            "representative_count":
                0,

            "signal_class":
                "PATIENT SIGNAL",

            "analysis_status":
                "no-data",

            "llm_context":
                "",

            "disclaimer":
                (
                    "No connected public "
                    "Patient Voice records were "
                    "available for analysis."
                ),
        }

    analyzed_items = [
        _normalize_item(
            item
        )
        for item in items
        if isinstance(
            item,
            dict,
        )
    ]

    total_items = len(
        analyzed_items
    )

    theme_counter = Counter(
        item[
            "primary_theme"
        ]
        for item
        in analyzed_items
    )

    theme_summary = []

    for theme, count in (
        theme_counter
        .most_common()
    ):
        share = (
            round(
                (
                    count
                    / total_items
                )
                * 100,
                1,
            )
            if total_items
            else 0.0
        )

        theme_summary.append(
            {
                "theme":
                    theme,

                "count":
                    count,

                "share_pct":
                    share,
            }
        )

    source_counter = Counter(
        _safe_text(
            item.get(
                "provider"
            )
            or item.get(
                "source"
            )
            or "Unknown"
        )
        for item
        in analyzed_items
    )

    source_summary = [
        {
            "source":
                source,

            "count":
                count,
        }
        for source, count
        in (
            source_counter
            .most_common()
        )
    ]

    top_themes = (
        theme_summary[:5]
    )

    representative_items = (
        select_representative_signals(
            analyzed_items
        )
    )

    representative_keys = {
        _safe_text(
            item.get("url")
            or item.get("id")
            or item.get("title")
        )
        for item
        in representative_items
    }

    analyzed_items = [
        {
            **item,

            "representative":
                (
                    _safe_text(
                        item.get("url")
                        or item.get("id")
                        or item.get("title")
                    )
                    in representative_keys
                ),
        }
        for item in analyzed_items
    ]

    llm_context = (
        build_patient_voice_context(
            representative_items
        )
    )

    return {
        "items":
            analyzed_items,

        "total_items":
            total_items,

        "theme_summary":
            theme_summary,

        "top_themes":
            top_themes,

        "source_summary":
            source_summary,

        "representative_items":
            representative_items,

        "representative_count":
            len(
                representative_items
            ),

        "signal_class":
            "PATIENT SIGNAL",

        "analysis_status":
            "hypothesis-generating",

        "analysis_method":
            (
                "All collected signals were "
                "rule-based classified. "
                "LLM synthesis uses aggregate counts "
                "plus representative signals."
            ),

        "llm_context":
            llm_context,

        "disclaimer":
            PATIENT_VOICE_DISCLAIMER,
    }


PATIENT_VOICE_PAGE_SIZE = 25


def paginate_patient_voice(
    items: list[
        dict[str, Any]
    ] | None,
    page: int = 1,
    page_size: int = (
        PATIENT_VOICE_PAGE_SIZE
    ),
) -> dict[str, Any]:

    items = [
        item
        for item in (
            items or []
        )
        if isinstance(
            item,
            dict,
        )
    ]

    page = max(
        1,
        int(page or 1),
    )

    page_size = max(
        1,
        min(
            int(
                page_size
                or
                PATIENT_VOICE_PAGE_SIZE
            ),
            100,
        ),
    )

    total_items = len(items)

    total_pages = max(
        1,
        (
            total_items
            + page_size
            - 1
        )
        // page_size,
    )

    page = min(
        page,
        total_pages,
    )

    start = (
        page - 1
    ) * page_size

    end = (
        start
        + page_size
    )

    return {
        "items":
            items[
                start:end
            ],

        "page":
            page,

        "page_size":
            page_size,

        "total_items":
            total_items,

        "total_pages":
            total_pages,

        "has_previous":
            page > 1,

        "has_next":
            end
            < total_items,

        "previous_page":
            (
                page - 1
                if page > 1
                else None
            ),

        "next_page":
            (
                page + 1
                if end
                < total_items
                else None
            ),
    }


def analyze_patient_voice_page(
    items: list[
        dict[str, Any]
    ] | None,
    page: int = 1,
    page_size: int = (
        PATIENT_VOICE_PAGE_SIZE
    ),
) -> dict[str, Any]:

    full_analysis = (
        analyze_patient_voice(
            items
        )
    )

    pagination = (
        paginate_patient_voice(
            items=
                full_analysis.get(
                    "items",
                    [],
                ),
            page=page,
            page_size=page_size,
        )
    )

    return {
        **full_analysis,

        "page_items":
            pagination[
                "items"
            ],

        "pagination": {
            "page":
                pagination[
                    "page"
                ],

            "page_size":
                pagination[
                    "page_size"
                ],

            "total_items":
                pagination[
                    "total_items"
                ],

            "total_pages":
                pagination[
                    "total_pages"
                ],

            "has_previous":
                pagination[
                    "has_previous"
                ],

            "has_next":
                pagination[
                    "has_next"
                ],

            "previous_page":
                pagination[
                    "previous_page"
                ],

            "next_page":
                pagination[
                    "next_page"
                ],
        },
    }