import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List
from urllib.parse import quote

import requests


ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

NCBI_TOOL = os.getenv("NCBI_TOOL", "MSL_ONE")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "")
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")

TIMEOUT = 25


def _base_params() -> Dict[str, str]:
    params = {
        "tool": NCBI_TOOL,
    }

    if NCBI_EMAIL:
        params["email"] = NCBI_EMAIL

    if NCBI_API_KEY:
        params["api_key"] = NCBI_API_KEY

    return params


def _node_text(node) -> str:
    if node is None:
        return ""

    return "".join(node.itertext()).strip()


def _article_title(article) -> str:
    node = article.find(".//ArticleTitle")
    return _node_text(node)


def _abstract(article) -> str:
    parts = []

    for node in article.findall(".//Abstract/AbstractText"):
        text = _node_text(node)
        label = node.attrib.get("Label", "").strip()

        if not text:
            continue

        if label:
            parts.append(f"{label}: {text}")
        else:
            parts.append(text)

    return "\n".join(parts).strip()


def _journal(article) -> str:
    node = article.find(".//Journal/Title")

    if node is not None:
        value = _node_text(node)
        if value:
            return value

    node = article.find(".//Journal/ISOAbbreviation")
    return _node_text(node)


def _publication_date(article) -> str:
    year = _node_text(article.find(".//PubDate/Year"))
    month = _node_text(article.find(".//PubDate/Month"))
    day = _node_text(article.find(".//PubDate/Day"))

    if year:
        return " ".join(
            value for value in [year, month, day] if value
        )

    medline_date = _node_text(
        article.find(".//PubDate/MedlineDate")
    )

    if medline_date:
        return medline_date

    article_date = article.find(".//ArticleDate")

    if article_date is not None:
        year = _node_text(article_date.find("Year"))
        month = _node_text(article_date.find("Month"))
        day = _node_text(article_date.find("Day"))

        return "-".join(
            value for value in [year, month, day] if value
        )

    return ""


def _doi(article) -> str:
    for node in article.findall(".//ArticleId"):
        if node.attrib.get("IdType") == "doi":
            return _node_text(node)

    return ""


def _pmid(article) -> str:
    node = article.find(".//PMID")
    return _node_text(node)


def _parse_articles(xml_text: str) -> List[Dict[str, Any]]:
    root = ET.fromstring(xml_text)

    records = []

    for article in root.findall(".//PubmedArticle"):
        pmid = _pmid(article)

        if not pmid:
            continue

        records.append(
            {
                "source": "PubMed",
                "evidence_class": "E1",
                "verified": True,
                "id": pmid,
                "pmid": pmid,
                "doi": _doi(article),
                "title": _article_title(article),
                "abstract": _abstract(article),
                "journal": _journal(article),
                "authors": [" ".join(filter(None, [_node_text(a.find('LastName')), _node_text(a.find('ForeName'))])) for a in article.findall('.//AuthorList/Author')],
                "affiliations": list(dict.fromkeys(_node_text(a) for a in article.findall('.//Affiliation') if _node_text(a))),
                "date": _publication_date(article),
                "status": "Peer-reviewed",
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            }
        )

    return records


def search_pubmed_paginated(
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
    page_size = max(1, min(int(page_size), 50))

    retstart = (page - 1) * page_size

    search_params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retstart": retstart,
        "retmax": page_size,
        "sort": "relevance",
        **_base_params(),
    }

    response = requests.get(
        ESEARCH_URL,
        params=search_params,
        timeout=TIMEOUT,
    )
    response.raise_for_status()

    payload = response.json()
    esearch_result = payload.get("esearchresult", {})

    total = int(esearch_result.get("count", 0) or 0)
    ids = esearch_result.get("idlist", []) or []

    if not ids:
        return {
            "items": [],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (
                (total + page_size - 1) // page_size
                if total
                else 0
            ),
        }

    fetch_params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml",
        **_base_params(),
    }

    fetch_response = requests.get(
        EFETCH_URL,
        params=fetch_params,
        timeout=TIMEOUT,
    )
    fetch_response.raise_for_status()

    items = _parse_articles(fetch_response.text)

    order = {pmid: index for index, pmid in enumerate(ids)}

    items.sort(
        key=lambda item: order.get(item.get("pmid"), 99999)
    )

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
    }


def search_pubmed(
    query: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    result = search_pubmed_paginated(
        query=query,
        page=1,
        page_size=limit,
    )

    return result["items"]
