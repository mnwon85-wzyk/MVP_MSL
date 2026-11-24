import json
import os
from datetime import datetime, timedelta, timezone
from typing import Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, SecretStr
import workflow_store as store
from workflow_sources import retrieve, source_key, fingerprint, source_date

class Context(BaseModel):
    hcp: str = ''
    disease: str = Field(min_length=1, max_length=200)
    biomarker: str = ''
    setting: str = ''
    scientific_question: str = ''
    related_question_id: str | None = None
    interaction_id: str | None = None
    evidence_gap: str = ''
    drugs: str = ''

class GeminiKeyRequest(BaseModel):
    api_key: SecretStr

def local_credentials_request(request):
    from urllib.parse import urlparse
    if request.client and request.client.host not in ('127.0.0.1', '::1', 'testclient'):
        raise HTTPException(403, 'API key settings are available only from localhost')
    origin = request.headers.get('origin')
    if origin and urlparse(origin).hostname not in ('localhost', '127.0.0.1', '::1'):
        raise HTTPException(403, 'API key settings require a local application origin')

class PrepareRequest(BaseModel):
    context: Context
    parent_id: str | None = None

class SessionPatch(BaseModel):
    revision: int
    selected_keys: list[str]
    selected_context: dict[Literal['treatment', 'signals', 'gaps'], list[str]] | None = None

class LanguageRequest(BaseModel):
    language: Literal['en', 'kr'] = 'en'
    revision: int

class InteractionRequest(BaseModel):
    prepare_id: str | None = None
    context: dict = Field(default_factory=dict)
    hcp: str = ''
    date: str = ''
    topic: str = ''
    observation: str = Field(min_length=1, max_length=12000)
    scientific_question: str = ''
    follow_up: str = ''

class QuestionRequest(BaseModel):
    interaction_id: str
    scientific_question: str = Field(min_length=1)
    evidence_gap: str = ''
    follow_up: str = ''

class QuestionPatch(BaseModel):
    status: Literal['OPEN', 'MONITOR', 'FOLLOW-UP', 'RESOLVED']
    follow_up_notes: str = ''

class TaskRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    complete: bool = False

def selected(session):
    return [i for i in session['evidence'] if source_key(i) in session.get('selected_keys', [])]

def basket_items(session):
    items = [{'category': 'evidence', 'key': source_key(i), 'record': i} for i in selected(session)]
    for category in ('treatment', 'signals', 'gaps'):
        records = session['signals'].get('items', []) if category == 'signals' else session.get(category, [])
        keys = session.get('selected_context', {}).get(category, [])
        items += [{'category': category, 'key': str(i['id']) if category == 'gaps' else source_key(i), 'record': i} for i in records if (str(i['id']) if category == 'gaps' else source_key(i)) in keys]
    return items

def parse_ai_json(answer):
    text = str(answer).strip()
    if text.startswith('```'):
        text = text.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        raise HTTPException(502, 'AI returned an unstructured response. Saved evidence is unchanged; retry or use the AI review package.')

def gaps_for(session):
    question = session['context'].get('scientific_question', '')
    if not question:
        return []
    return [{'id': 'question-review', 'kind': 'Unanswered scientific question', 'question': question, 'basis': 'Review whether the retrieved/selected source set addresses this question. Retrieval alone does not establish an answer or absence of evidence.', 'source_keys': [source_key(i) for i in selected(session)], 'review_required': True, 'method': 'Rule-derived review need; not a validated evidence gap'}]

def review_package(session, language='en'):
    questions = session.get('prior_questions', [])
    interaction = session.get('related_interaction')
    signals = session.get('signals', {}).get('items', [])
    sources = selected(session) + session['treatment'] + signals
    return {
        'product': 'MSL ONE',
        'context': session['context'],
        'scientific_question': session['context'].get('scientific_question'),
        'selected_evidence': selected(session),
        'selected_basket': basket_items(session),
        'regulatory_context': session['treatment'],
        'external_signals': signals,
        'potential_insight': interaction.get('analysis') if interaction else None,
        'evidence_gaps': session['gaps'],
        'follow_up_questions': questions,
        'changes_since_previous': session.get('comparison'),
        'source_urls': list(dict.fromkeys(i.get('url') for i in sources if i.get('url'))),
        'limitations': session['limitations'],
        'session_id': session['id'], 'revision': session['revision'],
        'searched_at': session['searched_at'], 'response_language': language,
        'instructions': 'Use only supplied sources. Preserve original titles and quotations. Separate source evidence from AI interpretation. Potential insights/gaps require medical review. Do not give treatment advice or invent citations.',
    }

def brief_text(session, language):
    kr = language == 'kr'
    def label(en, ko): return ko if kr else en
    context = session['context']
    lines = [label('HCP MEETING BRIEF', 'HCP 미팅 브리프'), '', label('HCP context', 'HCP 맥락'), ' · '.join(context.get(k, '') for k in ('hcp','disease','biomarker','setting') if context.get(k)), '', label('Scientific question', '과학적 질문'), context.get('scientific_question', ''), '', label('What changed since previous preparation', '이전 준비 이후 변화')]
    comparison = session.get('comparison')
    lines.append(label('No previous linked preparation. A new retrieval does not establish scientific change.', '연결된 이전 준비가 없습니다. 새 검색만으로 과학적 변화를 입증할 수 없습니다.') if not comparison else label(f"{len(comparison['newly_retrieved'])} newly retrieved; {len(comparison['updated_records'])} source records changed. Review source dates/content before drawing conclusions.", f"새로 검색된 자료 {len(comparison['newly_retrieved'])}건; 변경된 원문 기록 {len(comparison['updated_records'])}건. 결론 전 원문 날짜와 내용을 검토하세요."))
    lines += ['', label('Current approved regulatory context', '현재 승인 규제 맥락')]
    lines += [f"{i.get('source')} | {i.get('title')}\n{(i.get('indications') or i.get('therapeutic_indication', ''))[:500]}\n{i.get('url', '')}" for i in session['treatment'][:6]]
    if session['treatment']:
        lines.append(label(f"Showing up to 6 of {len(session['treatment'])} regulatory records, with source text excerpts. Review the full indication in Treatment / AI review package.", f"규제 기록 {len(session['treatment'])}건 중 최대 6건과 원문 발췌를 표시합니다. 전체 적응증은 치료 / AI 검토 패키지에서 확인하세요."))
    if not session['treatment']: lines.append(label('No verified context returned. This does not establish that no approved treatments exist.', '확인된 맥락이 반환되지 않았습니다. 승인 치료의 부재를 의미하지 않습니다.'))
    lines += ['', label('Selected relevant evidence / Source trace', '선택된 관련 근거 / 출처 추적')]
    lines += [f"[{n}] {i.get('source')} | {i.get('id', '')} | {i.get('title')}\n{i.get('abstract', '')[:700]}\n{i.get('url', '')}" for n,i in enumerate(selected(session), 1)]
    package = review_package(session, language)
    lines += ['', label('Previous open scientific questions', '이전 미해결 과학적 질문')]
    lines += [q['scientific_question'] for q in package['follow_up_questions']] or [label('None linked.', '연결된 질문 없음.')]
    lines += ['', label('Potential evidence gaps — Medical review required', '잠재적 근거 공백 — 메디컬 검토 필요')]
    lines += [g['question'] for g in session['gaps']]
    lines += ['', label('Potential scientific discussion question', '잠재적 과학적 논의 질문'), context.get('scientific_question', ''), '', label('Limitations', '제한 사항'), label('Source compilation, not an AI-validated conclusion. Verify original sources. Public signals are not validated clinical evidence. No treatment recommendations.', '출처 편집 자료이며 AI 검증 결론이 아닙니다. 원문을 확인하세요. 공개 신호는 검증된 임상 근거가 아닙니다. 치료 권고가 아닙니다.')]
    return '\n'.join(lines)

def make_router(legacy):
    router = APIRouter(prefix='/workflow')

    @router.get('/gemini')
    def gemini_status():
        return {'configured': bool(os.getenv('GEMINI_API_KEY', '').strip()), 'model': os.getenv('GEMINI_MODEL') or 'gemini-2.5-flash', 'storage': 'backend_process'}

    @router.put('/gemini')
    def configure_gemini(payload: GeminiKeyRequest, request: Request):
        local_credentials_request(request)
        key = payload.api_key.get_secret_value().strip()
        if not 20 <= len(key) <= 300 or any(c.isspace() for c in key):
            raise HTTPException(400, 'Enter a valid API key without spaces')
        os.environ['GEMINI_API_KEY'] = key
        return gemini_status()

    @router.post('/gemini/test')
    def test_gemini(request: Request):
        local_credentials_request(request)
        if not gemini_status()['configured']: raise HTTPException(400, 'Configure the Gemini API key first')
        try:
            legacy['_call_llm']('gemini', 'Connection test only.', 'Respond with OK. No scientific or user data is included.')
        except Exception:
            raise HTTPException(503, 'Gemini connection failed. Check the API key, model access, quota and network connection.')
        return {'connected': True, **gemini_status()}

    @router.post('/samples/gsk-oncology')
    def oncology_sample():
        from workflow_sample import create_sample
        session = create_sample()
        compilation = {'answer': brief_text(session, 'kr'), 'method':'Source compilation', 'selected_keys': session['selected_keys'], 'based_on_revision':session['revision'], 'generated_at':store.now()}
        return store.update_session(session['id'], {'briefs': {'kr':compilation, 'en':{**compilation, 'answer':brief_text(session, 'en')}}}, session['revision'])

    @router.get('/state')
    def state():
        summaries = [{k:s.get(k) for k in ('id','parent_id','context','created_at','updated_at','revision','searched_at','status')} for s in store.list_records('sessions')]
        return {'sessions': summaries, 'interactions': store.list_records('interactions'), 'questions': store.list_records('questions'), 'tasks': store.list_records('tasks'), 'note': store.setting('note') or '', 'context': store.setting('context') or {}, 'intelligence': store.setting('intelligence'), 'legacy_observations': legacy['get_hcp_insights']()['items']}

    @router.put('/note')
    def note(payload: dict):
        return {'note': store.setting('note', str(payload.get('note', ''))[:20000])}

    @router.put('/context')
    def context(payload: Context):
        return store.setting('context', payload.model_dump())

    @router.post('/tasks')
    def add_task(payload: TaskRequest):
        return store.save_record('tasks', payload.model_dump())

    @router.put('/tasks/{identifier}')
    def update_task(identifier: str, payload: TaskRequest):
        return store.save_record('tasks', payload.model_dump(), identifier)

    @router.delete('/tasks/{identifier}')
    def delete_task(identifier: str):
        with store.connect() as db: db.execute('DELETE FROM tasks WHERE id=?', (identifier,))
        return {'deleted': True}

    @router.post('/prepares')
    def create_prepare(payload: PrepareRequest):
        context = payload.context.model_dump()
        if not context['disease'].strip(): raise HTTPException(400, 'Disease is required')
        parent = store.get_session(payload.parent_id) if payload.parent_id else None
        if context.get('related_question_id'): store.get_record('questions', context['related_question_id'])
        if context.get('interaction_id'): store.get_record('interactions', context['interaction_id'])
        store.setting('context', context)
        previous_questions = [q for q in store.list_records('questions') if q['id'] == context.get('related_question_id') or context.get('hcp') and q['context'].get('hcp') == context['hcp'] and q['context'].get('disease') == context['disease']]
        prior_interaction = store.get_record('interactions', context['interaction_id']) if context.get('interaction_id') else None
        session = store.create_session({'context': context, 'prior_questions': previous_questions, 'related_interaction': prior_interaction, 'searched_at': None, 'status': 'searching', 'evidence': [], 'treatment': [], 'signals': {'status': 'not_loaded', 'items': []}, 'gaps': [], 'selected_keys': [], 'briefs': {}, 'analyses': {}, 'source_status': {}, 'limitations': []}, payload.parent_id)
        try:
            results = retrieve(context)
            comparison = None
            if parent:
                previous = {source_key(i): i for i in parent['evidence']}
                comparison = {'previous_session_id': parent['id'], 'previous_question': parent['context'].get('scientific_question'), 'previous_selected': selected(parent), 'newly_retrieved': [source_key(i) for i in results['evidence'] if source_key(i) not in previous], 'updated_records': [source_key(i) for i in results['evidence'] if source_key(i) in previous and fingerprint(i) != fingerprint(previous[source_key(i)])], 'interpretation': 'Newly retrieved/updated records; not confirmed scientific change.'}
            session = store.update_session(session['id'], {**results, 'status': 'complete', 'searched_at': store.now(), 'comparison': comparison}, session['revision'])
            return store.update_session(session['id'], {'gaps': gaps_for(session)}, session['revision'])
        except Exception:
            store.update_session(session['id'], {'status': 'failed'}, session['revision'])
            raise HTTPException(503, 'Retrieval unavailable. The session remains saved; retry with a new search.')

    @router.get('/prepares/{identifier}')
    def prepare(identifier: str, revision: int | None = None): return store.get_session(identifier, revision)

    @router.get('/prepares/{identifier}/versions')
    def versions(identifier: str):
        store.get_session(identifier)
        with store.connect() as db: return [dict(r) for r in db.execute('SELECT revision,saved_at FROM session_versions WHERE session_id=? ORDER BY revision DESC', (identifier,))]

    @router.patch('/prepares/{identifier}')
    def update_prepare(identifier: str, payload: SessionPatch):
        session = store.get_session(identifier)
        keys = {source_key(i) for i in session['evidence']}
        if not set(payload.selected_keys) <= keys: raise HTTPException(400, 'Selected evidence must belong to the session')
        context = payload.selected_context if payload.selected_context is not None else session.get('selected_context', {})
        for category, chosen in context.items():
            records = session['signals'].get('items', []) if category == 'signals' else session.get(category, [])
            allowed = {str(i['id']) if category == 'gaps' else source_key(i) for i in records}
            if not set(chosen) <= allowed: raise HTTPException(400, 'Selected basket items must belong to the saved session')
        return store.update_session(identifier, {'selected_keys': list(dict.fromkeys(payload.selected_keys)), 'selected_context': {k:list(dict.fromkeys(v)) for k,v in context.items()}}, payload.revision)

    @router.post('/prepares/{identifier}/signals')
    def signals(identifier: str, payload: LanguageRequest):
        session = store.get_session(identifier)
        if session['signals']['status'] == 'loaded': return session
        if payload.revision != session['revision']: raise HTTPException(409, 'Reopen the saved session before editing')
        query = ' '.join(filter(None, [session['context']['disease'], session['context'].get('biomarker')]))
        try:
            result = legacy['listen'](legacy['ListenRequest'](query=query, limit=30))
            source_states = list(result.get('source_status', {}).values())
            unavailable = not result.get('items') and source_states and all(s == 'unavailable' for s in source_states)
            data = {**result, 'status': 'unavailable' if unavailable else 'loaded', 'retrieved_at': store.now()}
        except Exception:
            data = {'status': 'unavailable', 'items': []}
        return store.update_session(identifier, {'signals': data}, payload.revision)

    @router.post('/prepares/{identifier}/brief')
    def brief(identifier: str, payload: LanguageRequest):
        session = store.get_session(identifier)
        if not selected(session): raise HTTPException(400, 'Select evidence before generating a brief')
        briefs = {**session.get('briefs', {}), payload.language: {'answer': brief_text(session, payload.language), 'generated_at': store.now(), 'selected_keys': session['selected_keys'], 'based_on_revision': session['revision'], 'method': 'Source compilation'}}
        return store.update_session(identifier, {'briefs': briefs}, payload.revision)

    @router.post('/prepares/{identifier}/analysis')
    def analysis(identifier: str, payload: LanguageRequest):
        session = store.get_session(identifier)
        basket = basket_items(session)
        if not basket: raise HTTPException(400, 'Select basket items before AI analysis')
        if payload.revision != session['revision']: raise HTTPException(409, 'Reopen the saved session before editing')
        try:
            answer = legacy['_call_llm']('gemini', 'You are a source-grounded Medical Affairs preparation assistant. Analyze ONLY the selected basket records supplied. Respond in the requested language. Include: scientific question and context, synthesis of selected evidence and regulatory context, selected public signals, selected potential gaps, discussion questions, limitations, and source trace with exact supplied identifiers and URLs. Cite each factual claim to its supplied source. Distinguish peer-reviewed evidence, investigational trial records, regulatory records, public signals (unvalidated and nonrepresentative), and derived gaps (interpretations requiring review). Never promote signals or gaps to clinical evidence. Do not infer evidence absence from limited retrieval. Do not invent citations or give treatment recommendations. Preserve original source titles.', json.dumps({'language': '한국어' if payload.language == 'kr' else 'English', 'context': session['context'], 'selected_basket': basket, 'limitations': session['limitations']}, ensure_ascii=False))
        except Exception:
            raise HTTPException(500, 'AI analysis unavailable. The selected basket remains saved.')
        result = {'answer': answer, 'generated_at': store.now(), 'based_on_revision': session['revision'], 'basket_items': basket, 'selected_context': session.get('selected_context', {}), 'method': 'AI-derived basket analysis'}
        result['selected_keys'] = session['selected_keys']
        return store.update_session(identifier, {'analyses': {**session.get('analyses', {}), payload.language: result}}, payload.revision)

    @router.post('/prepares/{identifier}/gaps')
    def derive_gaps(identifier: str, payload: LanguageRequest):
        session = store.get_session(identifier)
        if payload.revision != session['revision']: raise HTTPException(409, 'Reopen the saved session before editing')
        if not selected(session): raise HTTPException(400, 'Select evidence before AI analysis')
        package = review_package(session, payload.language)
        try:
            answer = legacy['_call_llm']('gemini', 'You assist scientific preparation. Use only the supplied sources. Separate source evidence from interpretation. Never infer absence of evidence from bounded retrieval. No treatment recommendations. Potential gaps require medical review. Return only JSON, an array of at most 5 objects: {"kind": string, "question": string, "basis": string, "source_keys": string[]}. Preserve exact supplied source_keys; never invent citations.', json.dumps({'language': payload.language, 'package':package, 'source_keys':[source_key(i) for i in selected(session)]}, ensure_ascii=False))
        except Exception:
            raise HTTPException(503, 'AI analysis unavailable. Saved evidence and review needs are preserved.')
        derived = parse_ai_json(answer)
        if not isinstance(derived, list) or len(derived) > 5: raise HTTPException(502, 'AI returned invalid gap structure')
        allowed = {source_key(i) for i in selected(session)}
        gaps = []
        for n, gap in enumerate(derived):
            if not isinstance(gap, dict) or not isinstance(gap.get('source_keys'), list) or not all(isinstance(k,str) and k in allowed for k in gap['source_keys']) or not all(isinstance(gap.get(k),str) for k in ('kind','question','basis')):
                raise HTTPException(502, 'AI returned invalid source references. Saved evidence is unchanged.')
            gaps.append({**gap, 'id':str(n), 'review_required':True, 'method':'AI-derived interpretation', 'generated_at':store.now()})
        return store.update_session(identifier, {'gaps':gaps, 'selected_context': {**session.get('selected_context', {}), 'gaps': []}}, payload.revision)

    @router.post('/prepares/{identifier}/signal-analysis')
    def analyze_signals(identifier: str, payload: LanguageRequest):
        session = store.get_session(identifier)
        if payload.revision != session['revision']: raise HTTPException(409, 'Reopen the saved session before editing')
        if not session['signals'].get('items'): raise HTTPException(400, 'Retrieved public signals are required')
        related = [r for r in store.list_records('interactions') if r['context'].get('hcp') == session['context'].get('hcp') and session['context'].get('hcp')]
        result = legacy['analyze'](legacy['AnalyzeRequest'](mode='listen', language='한국어' if payload.language == 'kr' else 'English', prompt=session['context'].get('scientific_question', ''), listen=session['signals'], hcp_insights=related))
        return store.update_session(identifier, {'signal_analyses': {**session.get('signal_analyses', {}), payload.language: result}}, payload.revision)

    @router.get('/prepares/{identifier}/package')
    def package(identifier: str, language: str = 'en', revision: int | None = None): return review_package(store.get_session(identifier, revision), language)

    @router.post('/interactions')
    def interaction(payload: InteractionRequest):
        values = payload.model_dump()
        if payload.prepare_id:
            session = store.get_session(payload.prepare_id)
            values['context'] = session['context']
            values['prepare_revision'] = session['revision']
            values['selected_evidence'] = selected(session)
            values['hcp'] = payload.hcp or session['context'].get('hcp', '')
        else:
            values['context'] = Context(**payload.context).model_dump()
        if not payload.observation.strip(): raise HTTPException(400, 'Observation is required')
        values['analysis'] = None
        return store.save_record('interactions', values)

    @router.post('/interactions/{identifier}/analyze')
    def analyze_interaction(identifier: str, payload: dict):
        record = store.get_record('interactions', identifier)
        structured = record.get('analysis') or {'observation': record['observation'], 'scientific_question': record['scientific_question'], 'potential_actionable_insight': None, 'evidence_gap': record['scientific_question'], 'unmet_need': None, 'strategic_relevance': None, 'supporting_evidence': record.get('selected_evidence', []), 'missing_evidence': record['scientific_question'], 'review_required': True, 'method': 'Structured field observation — interpretation not established'}
        # Save the field structure before attempting optional AI.
        record = store.save_record('interactions', {'analysis': structured}, identifier)
        if payload.get('use_ai'):
            try:
                result = legacy['analyze'](legacy['AnalyzeRequest'](mode='listen', language='한국어' if payload.get('language') == 'kr' else 'English', prompt='Return only a JSON object with string or null fields: observation, scientific_question, potential_actionable_insight, evidence_gap, unmet_need, strategic_relevance, missing_evidence. Separate observation from interpretation. Do not infer medical facts from a synthetic observation. Potential insight — Medical review required. ' + record['scientific_question'], hcp_insights=[record]))
                history = record.get('analysis_history', [])
                if structured.get('ai_interpretation'):
                    history = [*history, structured['ai_interpretation']]
                structured['ai_interpretation'] = result
                try:
                    parsed = parse_ai_json(result.get('answer', ''))
                    if isinstance(parsed, dict):
                        for field in ('potential_actionable_insight','evidence_gap','unmet_need','strategic_relevance','missing_evidence'):
                            if isinstance(parsed.get(field), str): structured[field] = parsed[field]
                except HTTPException:
                    pass  # Preserve free-form legacy analysis as a clearly labelled interpretation.
                record = store.save_record('interactions', {'analysis': structured, 'analysis_history': history, 'ai_status': 'available'}, identifier)
            except Exception:
                record = store.save_record('interactions', {'ai_status': 'unavailable'}, identifier)
        return record

    @router.post('/questions')
    def question(payload: QuestionRequest):
        record = store.get_record('interactions', payload.interaction_id)
        return store.save_record('questions', {**payload.model_dump(), 'prepare_id': record.get('prepare_id'), 'context': record['context'], 'selected_evidence': record.get('selected_evidence', []), 'status': 'OPEN', 'follow_up_notes': ''})

    @router.patch('/questions/{identifier}')
    def update_question(identifier: str, payload: QuestionPatch): return store.save_record('questions', payload.model_dump(), identifier)

    @router.post('/intelligence/refresh')
    def intelligence():
        context = store.setting('context')
        if not context or not context.get('disease'): raise HTTPException(400, 'Save a therapeutic context in Prepare first')
        result = retrieve(context, morning=True)
        previous = store.setting('intelligence') or {}
        same_context = all(previous.get('context', {}).get(k) == context.get(k) for k in ('disease','biomarker','setting'))
        prior = {source_key(i): i for i in previous.get('evidence', [])} if same_context else {}
        changes = []
        questions = [q for q in store.list_records('questions') if q['status'] != 'RESOLVED']
        for item in result['evidence']:
            key = source_key(item)
            if key in prior and fingerprint(item) == fingerprint(prior[key]): continue
            published = source_date(item)
            # Initial/newly discovered old records are context, not morning updates.
            if key not in prior and (not published or published < datetime.now(timezone.utc) - timedelta(days=30)):
                continue
            content = json.dumps(item, ensure_ascii=False).lower()
            matches = [q['id'] for q in questions if q['context'].get('disease', '').lower() == context['disease'].lower() and (not q['context'].get('biomarker') or q['context']['biomarker'].lower() in content)]
            changes.append({'evidence': item, 'kind': 'updated_record' if key in prior else 'newly_retrieved', 'question_ids': matches})
        changes.sort(key=lambda change: (bool(change['question_ids']), source_date(change['evidence']) or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        # Retain old snapshots for failing sources so a partial refresh cannot erase evidence.
        evidence = {source_key(i):i for i in previous.get('evidence', []) if same_context and result['source_status'].get(i.get('source'), {}).get('status') != 'ok'}
        evidence.update({source_key(i):i for i in result['evidence']})
        return store.setting('intelligence', {**result, 'evidence': list(evidence.values()), 'context': context, 'changes': changes, 'refreshed_at': store.now(), 'baseline': not same_context or not previous})

    return router
