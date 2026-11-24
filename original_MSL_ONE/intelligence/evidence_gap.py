from services.llm_router import ask_llm


SYSTEM_PROMPT = """
You are an Oncology Medical Affairs evidence synthesis assistant.

Rules:

1. Use only the evidence supplied in the context.
2. Do not invent efficacy, safety, biomarker, regulatory or trial claims.
3. Clearly separate:
   - established evidence
   - ongoing development
   - unanswered questions
   - potential evidence gaps
4. Failure to retrieve evidence does not prove that evidence does not exist.
5. Any evidence gap must be labelled "Potential Evidence Gap".
6. Do not provide treatment recommendations.
7. Preserve trial IDs, endpoints and numerical results exactly when present.
8. Keep the output non-promotional and scientifically balanced.
"""


def create_evidence_context(
    papers,
    trials,
    max_items=8,
):
    sections = []

    sections.append(
        "PEER-REVIEWED EVIDENCE"
    )

    for paper in papers[:max_items]:
        sections.append(
            f"""
PMID: {paper.get('id')}
Title: {paper.get('title')}
Abstract: {paper.get('abstract')}
URL: {paper.get('url')}
"""
        )

    sections.append(
        "\nCLINICAL DEVELOPMENT"
    )

    for trial in trials[:max_items]:
        sections.append(
            f"""
NCT: {trial.get('id')}
Title: {trial.get('title')}
Status: {trial.get('status')}
Phase: {trial.get('date')}
Conditions: {trial.get('conditions')}
URL: {trial.get('url')}
"""
        )

    return "\n".join(sections)


def analyze_evidence(
    provider,
    question,
    papers,
    trials,
):
    context = create_evidence_context(
        papers,
        trials,
    )

    prompt = f"""
SCIENTIFIC QUESTION

{question}

SOURCE MATERIAL

{context}

Create:

1. Evidence Snapshot
2. Development Landscape
3. Emerging Scientific Questions
4. Potential Evidence Gaps
5. Questions an MSL could explore scientifically

Add source IDs after relevant statements.
"""

    return ask_llm(
        provider,
        SYSTEM_PROMPT,
        prompt,
    )