from typing import Any, Dict, List
from urllib.parse import quote

import requests


FDA_LABEL_URL = (
    "https://api.fda.gov/drug/label.json"
)

FDA_DRUGSFDA_URL = (
    "https://api.fda.gov/drug/drugsfda.json"
)

REQUEST_TIMEOUT = 20


def _safe_get(
    data: Dict[str, Any],
    key: str,
    default="",
):
    value = data.get(key)

    if value is None:
        return default

    return value


def _first(value):
    if isinstance(value, list):
        return value[0] if value else ""

    return value or ""


def _text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return "\n".join(
            str(item)
            for item in value
            if item is not None
        ).strip()

    return str(value).strip()


def _deduplicate_records(
    records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    seen = set()
    result = []

    for record in records:
        openfda = record.get(
            "openfda",
            {},
        )

        if not isinstance(
            openfda,
            dict,
        ):
            openfda = {}

        key = (
            _first(
                record.get(
                    "set_id"
                )
            )
            or _first(
                record.get(
                    "application_number"
                )
            )
            or _first(
                openfda.get(
                    "application_number"
                )
            )
            or _first(
                openfda.get(
                    "brand_name"
                )
            )
            or _first(
                openfda.get(
                    "generic_name"
                )
            )
        )

        key = str(key).strip().lower()

        if not key:
            continue

        if key in seen:
            continue

        seen.add(key)
        result.append(record)

    return result


def _request_openfda(
    url: str,
    params: dict,
) -> dict:
    response = requests.get(
        url,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    if response.status_code == 404:
        return {
            "results": []
        }

    response.raise_for_status()

    return response.json()


def search_fda_label(
    drug_name: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    drug_name = (
        drug_name or ""
    ).strip()

    if not drug_name:
        return []

    escaped = drug_name.replace(
        '"',
        '\\"',
    )

    fields = [
        "openfda.generic_name",
        "openfda.brand_name",
        "openfda.substance_name",
    ]

    all_records = []

    for field in fields:
        try:
            payload = _request_openfda(
                FDA_LABEL_URL,
                {
                    "search": (
                        f'{field}:"{escaped}"'
                    ),
                    "limit": min(
                        max(
                            int(limit),
                            1,
                        ),
                        20,
                    ),
                },
            )

            results = payload.get(
                "results",
                [],
            )

            if isinstance(
                results,
                list,
            ):
                all_records.extend(
                    results
                )

        except Exception:
            continue

    return _deduplicate_records(
        all_records
    )[:limit]


def normalize_label(
    record: Dict[str, Any]
) -> Dict[str, Any]:
    openfda = record.get(
        "openfda",
        {},
    )

    if not isinstance(
        openfda,
        dict,
    ):
        openfda = {}

    brand_name = _first(
        openfda.get(
            "brand_name"
        )
    )

    generic_name = _first(
        openfda.get(
            "generic_name"
        )
    )

    substance_name = _first(
        openfda.get(
            "substance_name"
        )
    )

    manufacturer = _first(
        openfda.get(
            "manufacturer_name"
        )
    )

    application_number = (
        _first(
            openfda.get(
                "application_number"
            )
        )
        or _first(
            record.get(
                "application_number"
            )
        )
    )

    spl_set_id = (
        record.get(
            "set_id"
        )
        or record.get(
            "spl_set_id"
        )
        or ""
    )

    product_type = _first(
        openfda.get(
            "product_type"
        )
    )

    route = _text(
        openfda.get(
            "route"
        )
    )

    dosage_form = _text(
        openfda.get(
            "dosage_form"
        )
    )

    effective_time = _text(
        record.get(
            "effective_time"
        )
    )

    indications = _text(
        record.get(
            "indications_and_usage"
        )
    )

    dosage = _text(
        record.get(
            "dosage_and_administration"
        )
    )

    warnings = _text(
        record.get(
            "warnings_and_cautions"
        )
    )

    adverse_reactions = _text(
        record.get(
            "adverse_reactions"
        )
    )

    clinical_studies = _text(
        record.get(
            "clinical_studies"
        )
    )

    boxed_warning = _text(
        record.get(
            "boxed_warning"
        )
    )

    contraindications = _text(
        record.get(
            "contraindications"
        )
    )

    mechanism_of_action = _text(
        record.get(
            "mechanism_of_action"
        )
    )

    pharmacodynamics = _text(
        record.get(
            "pharmacodynamics"
        )
    )

    pharmacokinetics = _text(
        record.get(
            "pharmacokinetics"
        )
    )

    use_in_specific_populations = _text(
        record.get(
            "use_in_specific_populations"
        )
    )

    drug_interactions = _text(
        record.get(
            "drug_interactions"
        )
    )

    return {
        "source": "FDA",
        "source_dataset":
            "openFDA Drug Label",
        "evidence_class": "R1",
        "verified": True,

        "brand_name": brand_name,
        "generic_name": generic_name,
        "substance_name": substance_name,

        "manufacturer": manufacturer,
        "application_number":
            application_number,
        "spl_set_id": spl_set_id,

        "product_type": product_type,
        "route": route,
        "dosage_form": dosage_form,
        "effective_time":
            effective_time,

        "indications": indications,
        "dosage": dosage,
        "warnings": warnings,
        "adverse_reactions":
            adverse_reactions,
        "clinical_studies":
            clinical_studies,
        "boxed_warning":
            boxed_warning,
        "contraindications":
            contraindications,

        "mechanism_of_action":
            mechanism_of_action,

        "pharmacodynamics":
            pharmacodynamics,

        "pharmacokinetics":
            pharmacokinetics,

        "use_in_specific_populations":
            use_in_specific_populations,

        "drug_interactions":
            drug_interactions,

        "source_url":
            FDA_LABEL_URL,
    }


def search_drugs_fda(
    drug_name: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    drug_name = (
        drug_name or ""
    ).strip()

    if not drug_name:
        return []

    escaped = drug_name.replace(
        '"',
        '\\"',
    )

    fields = [
        "openfda.generic_name",
        "openfda.brand_name",
    ]

    all_records = []

    for field in fields:
        try:
            payload = _request_openfda(
                FDA_DRUGSFDA_URL,
                {
                    "search": (
                        f'{field}:"{escaped}"'
                    ),
                    "limit": min(
                        max(
                            int(limit),
                            1,
                        ),
                        50,
                    ),
                },
            )

            results = payload.get(
                "results",
                [],
            )

            if isinstance(
                results,
                list,
            ):
                all_records.extend(
                    results
                )

        except Exception:
            continue

    return _deduplicate_records(
        all_records
    )[:limit]


def normalize_application(
    record: Dict[str, Any]
) -> Dict[str, Any]:
    openfda = record.get(
        "openfda",
        {},
    )

    if not isinstance(
        openfda,
        dict,
    ):
        openfda = {}

    application_number = _text(
        record.get(
            "application_number"
        )
    )

    sponsor = _text(
        record.get(
            "sponsor_name"
        )
    )

    products = record.get(
        "products",
        [],
    )

    if not isinstance(
        products,
        list,
    ):
        products = []

    normalized_products = []

    for product in products:
        if not isinstance(
            product,
            dict,
        ):
            continue

        normalized_products.append(
            {
                "product_number":
                    _text(
                        product.get(
                            "product_number"
                        )
                    ),

                "reference_drug":
                    _text(
                        product.get(
                            "reference_drug"
                        )
                    ),

                "brand_name":
                    _text(
                        product.get(
                            "brand_name"
                        )
                    ),

                "active_ingredients":
                    product.get(
                        "active_ingredients",
                        [],
                    ),

                "dosage_form":
                    _text(
                        product.get(
                            "dosage_form"
                        )
                    ),

                "route":
                    _text(
                        product.get(
                            "route"
                        )
                    ),

                "marketing_status":
                    _text(
                        product.get(
                            "marketing_status"
                        )
                    ),
            }
        )

    submissions = record.get(
        "submissions",
        [],
    )

    if not isinstance(
        submissions,
        list,
    ):
        submissions = []

    normalized_submissions = []

    for submission in submissions:
        if not isinstance(
            submission,
            dict,
        ):
            continue

        normalized_submissions.append(
            {
                "submission_type":
                    _text(
                        submission.get(
                            "submission_type"
                        )
                    ),

                "submission_number":
                    _text(
                        submission.get(
                            "submission_number"
                        )
                    ),

                "submission_status":
                    _text(
                        submission.get(
                            "submission_status"
                        )
                    ),

                "submission_status_date":
                    _text(
                        submission.get(
                            "submission_status_date"
                        )
                    ),

                "review_priority":
                    _text(
                        submission.get(
                            "review_priority"
                        )
                    ),
            }
        )

    brand_name = _first(
        openfda.get(
            "brand_name"
        )
    )

    generic_name = _first(
        openfda.get(
            "generic_name"
        )
    )

    return {
        "source": "FDA",
        "source_dataset":
            "Drugs@FDA",

        "evidence_class": "R1",
        "verified": True,

        "application_number":
            application_number,

        "sponsor": sponsor,

        "brand_name":
            brand_name,

        "generic_name":
            generic_name,

        "products":
            normalized_products,

        "submissions":
            normalized_submissions,

        "url":
            fda_drugs_page(
                application_number
            ),
    }


def fda_drugs_page(
    application_number: str,
) -> str:
    application_number = (
        application_number or ""
    ).strip()

    if not application_number:
        return ""

    number = (
        application_number
        .upper()
        .replace(
            "NDA",
            "",
        )
        .replace(
            "BLA",
            "",
        )
        .replace(
            "ANDA",
            "",
        )
        .strip()
    )

    if not number:
        return ""

    return (
        "https://www.accessdata.fda.gov/"
        "scripts/cder/daf/index.cfm"
        "?event=overview.process"
        f"&ApplNo={quote(number)}"
    )


def get_fda_drug_profile(
    drug_name: str,
) -> Dict[str, Any]:
    labels = search_fda_label(
        drug_name,
        limit=5,
    )

    applications = (
        search_drugs_fda(
            drug_name,
            limit=10,
        )
    )

    normalized_label = None

    if labels:
        try:
            normalized_label = (
                normalize_label(
                    labels[0]
                )
            )
        except Exception:
            normalized_label = None

    normalized_apps = []

    for item in applications:
        try:
            normalized_apps.append(
                normalize_application(
                    item
                )
            )
        except Exception:
            continue

    return {
        "query": drug_name,
        "label_found":
            normalized_label
            is not None,

        "application_found":
            bool(
                normalized_apps
            ),

        "label":
            normalized_label,

        "applications":
            normalized_apps,
    }