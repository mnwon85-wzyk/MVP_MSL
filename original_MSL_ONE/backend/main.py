# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.pubmed import search_pubmed
from services.clinicaltrials import search_trials

try:
    from services.fda import search_fda_label, normalize_label
except Exception:
    search_fda_label = None
    normalize_label = None


app = FastAPI(title="MSL ONE API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SearchRequest(BaseModel):
    query: str
    sources: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search")
def search(req: SearchRequest):

    query = req.query.strip()
    sources = req.sources

    papers = []
    trials = []
    fda = None
    errors = []

    if not query:
        return {
            "query": "",
            "papers": [],
            "trials": [],
            "fda": None,
            "errors": ["Search term is required."],
        }

    if "PubMed" in sources:
        try:
            papers = search_pubmed(
                query,
                max_results=15,
            )
        except Exception as exc:
            errors.append(
                f"PubMed: {exc}"
            )

    if "ClinicalTrials.gov" in sources:
        try:
            trials = search_trials(
                query,
                page_size=15,
            )
        except Exception as exc:
            errors.append(
                f"ClinicalTrials.gov: {exc}"
            )

    if "FDA" in sources:
        try:
            if search_fda_label and normalize_label:

                result = search_fda_label(query)

                if result:
                    fda = normalize_label(result[0])

        except Exception as exc:
            errors.append(
                f"FDA: {exc}"
            )

    if "EMA" in sources:
        errors.append(
            "EMA retrieval is not connected yet."
        )

    return {
        "query": query,
        "papers": papers,
        "trials": trials,
        "fda": fda,
        "errors": errors,
    }