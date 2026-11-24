"""Bounded retrieval using existing source adapters and normalizers."""
from concurrent.futures import ThreadPoolExecutor, wait
import hashlib
import json
from datetime import datetime, timezone
from urllib.parse import urlencode
import requests
from services.pubmed import search_pubmed_paginated
from services.clinicaltrials import search_trials_paginated
from services.ema import search_ema_medicines
from services.fda import normalize_label, fda_drugs_page, FDA_LABEL_URL
from services.landscape import COMMON_DISEASE_EXPANSIONS, _indication_matches

def source_key(item):
    return f"{item.get('source')}:{item.get('id') or item.get('pmid') or item.get('url') or item.get('title')}"

def fingerprint(item):
    scientific = {k: item.get(k) for k in ('title', 'abstract', 'indications', 'therapeutic_indication', 'status', 'updated_date')}
    if item.get('source') == 'FDA':
        # A UI fallback from blank title to label UUID is not a source change.
        scientific['title'] = item.get('brand_name') or item.get('generic_name') or ''
    return hashlib.sha256(json.dumps(scientific, sort_keys=True).encode()).hexdigest()

def source_date(item):
    value = str(item.get('source_date') or item.get('updated_date') or item.get('date') or '')
    for fmt in ('%Y-%m-%d', '%Y%m%d', '%d/%m/%Y', '%Y %b %d', '%Y %b'):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None

def disease_terms(disease):
    return COMMON_DISEASE_EXPANSIONS.get(disease.lower().strip(), [disease])

def fda_context(context):
    # Labels alone do not prove approval. Verify the corresponding NDA/BLA submission.
    terms = disease_terms(context['disease'])
    escaped = [term.replace('"', '').replace('\\', '') for term in terms]
    query = ' OR '.join(f'indications_and_usage:"{term}"' for term in escaped)
    drugs = [s.strip().replace('"', '').replace('\\', '') for s in context.get('drugs', '').split(',') if s.strip()]
    if drugs:
        query = '(' + query + ') AND (' + ' OR '.join(f'openfda.generic_name:"{drug}" OR openfda.brand_name:"{drug}"' for drug in drugs) + ')'
    response = requests.get(FDA_LABEL_URL, params={'search': query, 'limit': 12}, timeout=20)
    if response.status_code == 404:
        return {'evidence': [], 'treatment': []}
    response.raise_for_status()
    evidence, treatments, verified = [], [], {}
    for raw in response.json().get('results', []):
        label = normalize_label(raw)
        application = label.get('application_number', '')
        spl_id = raw.get('set_id') or raw.get('id')
        specific_label_url = FDA_LABEL_URL + '?' + urlencode({'search': f'set_id:"{spl_id}"'}) if raw.get('set_id') else ''
        item = {**label, 'source': 'FDA', 'id': application or spl_id, 'title': label.get('brand_name') or label.get('generic_name') or application or spl_id, 'abstract': label.get('indications', ''), 'url': fda_drugs_page(application) if application else specific_label_url, 'date': label.get('effective_time', ''), 'source_date': label.get('effective_time', '')}
        evidence.append(item)
        if not application.startswith(('NDA', 'BLA')) or not _indication_matches(item['abstract'], context['disease']):
            continue
        if application not in verified:
            approval = requests.get('https://api.fda.gov/drug/drugsfda.json', params={'search': f'application_number:"{application}"', 'limit': 1}, timeout=15)
            if approval.status_code == 404:
                verified[application] = False
            else:
                approval.raise_for_status()
                verified[application] = any(s.get('submission_status') == 'AP' for r in approval.json().get('results', []) for s in r.get('submissions', []))
        if verified[application]:
            treatments.append({**item, 'approval_basis': 'FDA approved application + disease indication text; biomarker/setting fit requires review'})
    return {'evidence': evidence, 'treatment': treatments}

def ema_context(context):
    records = []
    terms = [s.strip() for s in context.get('drugs', '').split(',') if s.strip()] or disease_terms(context['disease'])[:3]
    for term in terms:
        records.extend(search_ema_medicines(term, limit=12))
    records = list({source_key(r): r for r in records}.values())
    treatment = [{**r, 'approval_basis': 'EMA authorised status + disease indication text; biomarker/setting fit requires review'} for r in records if str(r.get('status', '')).lower() in {'authorised', 'authorized'} and _indication_matches(r.get('therapeutic_indication', ''), context['disease'])]
    return {'evidence': records, 'treatment': treatment}

def retrieve(context, morning=False):
    terms = disease_terms(context['disease'])
    disease_query = '(' + ' OR '.join(f'"{term}"' for term in terms) + ')'
    modifiers = ' '.join(context.get(k, '') for k in ('biomarker', 'setting')).strip()
    pubmed_query = disease_query + (' AND ' + modifiers if modifiers else '')
    drug_terms = [s.strip().replace('"', '').replace('\\', '') for s in context.get('drugs', '').split(',') if s.strip()]
    if drug_terms:
        # Preserve clinical setting in the review context; don't require a free-text
        # meeting description to occur verbatim in a paper about the selected drugs.
        pubmed_query = disease_query + ' AND (' + ' OR '.join(f'"{term}"' for term in drug_terms) + ')'
    if morning:
        pubmed_query += ' AND ("last 30 days"[EDAT])'
    trial_query = ' '.join(filter(None, [context['disease'], modifiers]))
    if drug_terms: trial_query = context['disease'] + ' AND (' + ' OR '.join(f'"{term}"' for term in drug_terms) + ')'
    calls = {
        'PubMed': lambda: search_pubmed_paginated(pubmed_query, page_size=20),
        'ClinicalTrials.gov': lambda: search_trials_paginated(trial_query, page_size=20),
        'FDA': lambda: fda_context(context),
        'EMA': lambda: ema_context(context),
    }
    executor = ThreadPoolExecutor(max_workers=4)
    futures = {executor.submit(call): name for name, call in calls.items()}
    done, pending = wait(futures, timeout=55)
    evidence, treatment, statuses, totals = [], [], {}, {}
    for future, name in futures.items():
        if future in pending:
            statuses[name] = {'status': 'timeout'}
            future.cancel()
            continue
        try:
            value = future.result()
            items = value.get('items', value.get('evidence', []))
            evidence.extend(items)
            treatment.extend(value.get('treatment', []))
            totals[name] = value.get('total', len(items))
            statuses[name] = {'status': 'ok', 'count': len(items)}
        except Exception:
            statuses[name] = {'status': 'unavailable'}
    executor.shutdown(wait=False, cancel_futures=True)
    evidence = list({source_key(i): i for i in evidence}.values())
    treatment = list({source_key(i): i for i in treatment}.values())
    return {'evidence': evidence, 'treatment': treatment, 'source_status': statuses, 'source_totals': totals, 'queries': {'PubMed': pubmed_query, 'ClinicalTrials.gov': trial_query}, 'limitations': ['Bounded retrieval, not an exhaustive systematic review.', 'Approved application/authorisation and disease match do not establish biomarker or setting eligibility.', 'Public signals are hypothesis-generating; medical review is required.']}
