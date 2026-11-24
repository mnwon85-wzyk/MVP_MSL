"""A fictional HCP visit with real, traceable source records, not AI output."""
from concurrent.futures import ThreadPoolExecutor
import requests
import workflow_store as store
from workflow_sources import source_key
from services.pubmed import EFETCH_URL, _parse_articles, _base_params
from services.clinicaltrials import normalize_trial

CONTEXT = {
    'hcp': 'DEMO · Gynecologic oncologist using Keytruda',
    'disease': 'Endometrial cancer',
    'biomarker': 'dMMR / pMMR',
    'setting': 'Primary advanced or recurrent disease; first-line systemic treatment',
    'drugs': 'dostarlimab, pembrolizumab',
    'scientific_question': '진행성·재발성 자궁내막암에서 Jemperli(dostarlimab, GSK)와 Keytruda(pembrolizumab, MSD/Merck)의 RUBY 및 NRG-GY018 데이터를 해석할 때 시험 설계, 환자군, MMR 하위군, 평가변수, 추적기간, 유지요법, 안전성·삶의 질의 차이는 무엇인가? 비교 가능한 정보와 제한되는 정보, HCP와 논의할 질문을 출처와 함께 정리하고 시험 간 수치만으로 우월성을 추론하지 말 것.',
}

REGULATORY = [
    {'source':'FDA', 'id':'JEMPERLI-EC-20240801', 'title':'FDA expands endometrial cancer indication for dostarlimab-gxly with chemotherapy', 'date':'2024-08-01', 'url':'https://www.fda.gov/drugs/resources-information-approved-drugs/fda-expands-endometrial-cancer-indication-dostarlimab-gxly-chemotherapy', 'indications':'Dated FDA approval summary (2024-08-01): dostarlimab-gxly with carboplatin and paclitaxel, followed by single-agent dostarlimab-gxly, for adults with primary advanced or recurrent endometrial cancer. This is a curated summary, not the full prescribing information or verification of the current local label.', 'approval_basis':'FDA approval announcement dated 2024-08-01; current label and local eligibility require review'},
    {'source':'FDA', 'id':'KEYTRUDA-EC-20240617', 'title':'FDA approves pembrolizumab with chemotherapy for primary advanced or recurrent endometrial carcinoma', 'date':'2024-06-17', 'url':'https://www.fda.gov/drugs/resources-information-approved-drugs/fda-approves-pembrolizumab-chemotherapy-primary-advanced-or-recurrent-endometrial-carcinoma', 'indications':'Dated FDA approval summary (2024-06-17): pembrolizumab with carboplatin and paclitaxel, followed by single-agent pembrolizumab, for adults with primary advanced or recurrent endometrial carcinoma. This is a curated summary, not the full prescribing information or verification of the current local label.', 'approval_basis':'FDA approval announcement dated 2024-06-17; current label and local eligibility require review'},
]

def literature():
    response = requests.get(EFETCH_URL, params={'db':'pubmed','id':'36972026,36972022,40616865,40044930','retmode':'xml', **_base_params()}, timeout=25)
    response.raise_for_status()
    return _parse_articles(response.text)

def trial(identifier):
    response = requests.get(f'https://clinicaltrials.gov/api/v2/studies/{identifier}', timeout=25)
    response.raise_for_status()
    return [normalize_trial(response.json())]

def create_sample():
    evidence, status = [], {'FDA':{'status':'ok','count':2,'basis':'Curated dated FDA announcements'}}
    with ThreadPoolExecutor(max_workers=3) as pool:
        jobs = [('PubMed',pool.submit(literature)), ('RUBY',pool.submit(trial,'NCT03981796')), ('NRG-GY018',pool.submit(trial,'NCT03914612'))]
        for name, job in jobs:
            try:
                items = job.result()
                evidence += items
                status[name] = {'status':'ok','count':len(items)}
            except Exception:
                status[name] = {'status':'unavailable'}
    for record in REGULATORY:
        evidence.append({**record, 'abstract':record['indications'], 'source_date':record['date'], 'content_kind':'Curated dated regulatory summary'})
    gaps = [{'id':'sample-comparability', 'question':'Can RUBY and NRG-GY018 results be compared directly despite differences in populations, endpoints, follow-up and maintenance duration?', 'basis':'Two separate randomized studies do not constitute a head-to-head comparison. Review original protocols and analysis populations before interpreting cross-trial differences.', 'source_keys':[source_key(i) for i in evidence if i.get('id') in ('36972026','36972022','NCT03981796','NCT03914612')], 'method':'Rule-derived review need; not a validated evidence gap', 'review_required':True}]
    limitations = ['Fictional HCP visit; source records are real. This sample is not Gemini-generated analysis.', 'Curated starting set, not an exhaustive or automatically current literature review. Check later updates and local prescribing information.', 'FDA announcements are dated regulatory summaries, not full original indication text.', 'No head-to-head superiority conclusion can be drawn from separate trial results.', 'Public signals are not selected as efficacy evidence.']
    return store.create_session({'context':CONTEXT, 'status':'complete', 'searched_at':store.now(), 'evidence':evidence, 'treatment':REGULATORY, 'signals':{'status':'not_loaded','items':[]}, 'gaps':gaps, 'selected_keys':[source_key(i) for i in evidence if i['source'] != 'FDA'], 'selected_context':{'treatment':[source_key(i) for i in REGULATORY], 'gaps':['sample-comparability']}, 'source_status':status, 'source_totals':{}, 'limitations':limitations, 'briefs':{}, 'analyses':{}, 'prior_questions':[], 'related_interaction':None, 'comparison':None, 'sample':True})
