import {useEffect, useRef, useState} from 'react';
import {ArrowRight, Plus, Trash2, RefreshCw, CheckCircle2} from 'lucide-react';
import {request, date, API} from './api';
import {PageHeading, EvidenceList} from './components';

export default function DashboardPage({t, lang, state, reload, prepare}) {
  const [task, setTask] = useState('');
  const [note, setNote] = useState(state.note);
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const noteTimer = useRef(); const noteChain = useRef(Promise.resolve()); const touched = useRef(false);
  const autoStarted = useRef(false);
  const latestNote = useRef(note);
  const notePending = useRef(false);
  const intelligence = state.intelligence;
  const activeQuestions = state.questions.filter(q => q.status !== 'RESOLVED');
  useEffect(() => {if (!touched.current) setNote(state.note);}, [state.note]);
  function persistNote(value) {
    setSaving(true);
    noteChain.current = noteChain.current.catch(() => {}).then(() => request('/note', {note:value}, 'PUT')).then(async () => {await reload(); setSaving(false);}).catch(e => {setNotice(e.message); setSaving(false);});
  }
  function editNote(value) {touched.current = true; latestNote.current = value; notePending.current = true; setNote(value); clearTimeout(noteTimer.current); setSaving(true); noteTimer.current = setTimeout(() => persistNote(value), 500);}
  useEffect(() => () => {clearTimeout(noteTimer.current);}, []);
  useEffect(() => {
    function flushNote() {
      if (!notePending.current) return;
      fetch(`${API}/workflow/note`, {method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({note:latestNote.current}), keepalive:true}).catch(() => {});
    }
    window.addEventListener('pagehide', flushNote);
    return () => {window.removeEventListener('pagehide', flushNote); flushNote();};
  }, []);
  async function act(action) {setNotice(''); try {await action(); await reload();} catch(e) {setNotice(e.message);} }
  async function refresh() {setBusy(true); await act(() => request('/intelligence/refresh', {})); setBusy(false);}
  useEffect(() => {
    if (autoStarted.current || !state.context.disease) return;
    autoStarted.current = true;
    if (!intelligence || Date.now() - new Date(intelligence.refreshed_at).getTime() > 6 * 60 * 60 * 1000) {
      Promise.resolve().then(() => {setBusy(true); return request('/intelligence/refresh', {});})
        .then(reload).catch(e => setNotice(e.message)).finally(() => setBusy(false));
    }
  }, [intelligence, state.context.disease, reload]);
  return <>
    <PageHeading eyebrow={t('YOUR SCIENTIFIC DAY', '오늘의 과학적 업무')} title={t('What matters today?', '오늘 무엇이 중요한가요?')} description={new Date().toLocaleDateString(lang === 'kr' ? 'ko-KR' : 'en-GB', {timeZone:'Asia/Seoul', weekday:'long', day:'numeric', month:'long', year:'numeric'})}><button className="primary" onClick={() => prepare(state.context)}>{t('Prepare an exchange', '교류 준비')}<ArrowRight size={16}/></button></PageHeading>
    {notice && <div className="notice error" role="alert">{notice}</div>}
    <div className="day-grid"><section className="surface"><div className="section-heading"><h2>{t('My day', '오늘의 할 일')}</h2><span className="micro-label">{state.tasks.filter(task => task.complete).length} / {state.tasks.length}</span></div>
      <form className="inline-form" onSubmit={e => {e.preventDefault(); if(task.trim()) act(async () => {await request('/tasks',{title:task.trim()}); setTask('');});}}><input aria-label={t('New task', '새 할 일')} placeholder={t('Add a scientific task…', '과학적 업무 추가…')} value={task} onChange={e => setTask(e.target.value)}/><button aria-label={t('Add task', '할 일 추가')} disabled={!task.trim()}><Plus size={18}/></button></form>
      {state.tasks.length ? <div className="tasks">{state.tasks.map(item => <div key={item.id} className="task"><input aria-label={t('Mark complete', '완료 표시')} type="checkbox" checked={item.complete} onChange={() => act(() => request(`/tasks/${item.id}`, {...item, complete:!item.complete}, 'PUT'))}/><span className={item.complete ? 'complete' : ''}>{item.title}</span><button className="icon-button" aria-label={t('Delete task', '할 일 삭제')} onClick={() => act(() => request(`/tasks/${item.id}`, undefined, 'DELETE'))}><Trash2 size={15}/></button></div>)}</div> : <p className="muted empty-small">{t('A clear day. Add your first task.', '첫 할 일을 추가하세요.')}</p>}</section>
      <section className="surface"><div className="section-heading"><h2>{t('Quick note', '빠른 메모')}</h2><span className="micro-label">{saving ? t('Saving…', '저장 중…') : t('Saved to SQLite', 'SQLite에 저장됨')}</span></div><textarea className="quick-note" aria-label={t('Quick note', '빠른 메모')} placeholder={t('Keep a thought for your next scientific exchange…', '다음 과학적 교류를 위한 생각을 남기세요…')} value={note} onChange={e => editNote(e.target.value)} onBlur={() => {clearTimeout(noteTimer.current); persistNote(note);}}/><button className="text-button" onClick={() => {clearTimeout(noteTimer.current); persistNote(note);}}>{t('Save note', '메모 저장')}</button></section></div>
    <div className="dashboard-grid"><section className="surface intelligence"><div className="section-heading"><div><div className="eyebrow">{t('SOURCE EVIDENCE', '출처 근거')}</div><h2>{t('Morning intelligence', '모닝 인텔리전스')}</h2></div><button className="secondary" disabled={busy || !state.context.disease} onClick={refresh}><RefreshCw size={15} className={busy ? 'spinning' : ''}/>{busy ? t('Retrieving…', '조회 중…') : t('Refresh', '새로 조회')}</button></div>
      <div className="context-line">{state.context.disease ? [state.context.disease, state.context.biomarker, state.context.setting].filter(Boolean).join(' · ') : t('Save a therapeutic context in Prepare to begin.', '준비에서 치료 영역 맥락을 저장하면 시작됩니다.')}</div>
      {intelligence && <><p className="muted small">{t('Last checked', '최근 확인')}: {date(intelligence.refreshed_at, lang)}</p>{Object.entries(intelligence.source_status).map(([source,value]) => <span key={source} className={`status ${value.status === 'ok' ? '' : 'failed'}`}>{source} · {value.status === 'ok' ? t('Available', '연결됨') : t('Unavailable / timeout', '이용 불가 / 시간 초과')}</span>)}
      <p className="notice">{intelligence.baseline ? t('Initial source snapshot. Newly retrieved records are not confirmed scientific changes.', '첫 출처 스냅샷입니다. 새 검색 자료는 확인된 과학적 변화가 아닙니다.') : t('Records newly retrieved or changed since the previous check. Review source dates and original text.', '이전 확인 이후 새로 조회되거나 변경된 기록입니다. 원문 날짜와 내용을 검토하세요.')}</p>
      {!intelligence.changes.length ? <div className="empty"><CheckCircle2 size={26}/>{t('No newly retrieved or changed records in this bounded check.', '이번 제한된 조회에서 새로 검색되거나 변경된 기록이 없습니다.')}</div> : intelligence.changes.slice(0,8).map((change, i) => <div className="intelligence-item" key={i}><div className="micro-label">{t('WHAT CHANGED', '변경 사항')} · {change.kind === 'updated_record' ? t('Updated source record', '변경된 출처 기록') : t('Newly retrieved', '새로 조회됨')}</div><EvidenceList items={[change.evidence]} t={t}/><p className="small muted">{t('WHY IT MAY MATTER', '관련성')} · {t('Matches saved therapeutic context; scientific relevance requires review.', '저장된 치료 영역 맥락과 일치하며 과학적 관련성 검토가 필요합니다.')}</p>{change.question_ids.length > 0 && <p className="small">{t('Potentially relevant to an open question — does not establish resolution.', '미해결 질문과 잠재적 관련성 — 해결을 입증하지 않습니다.')}</p>}<button className="text-button" onClick={() => {const q=state.questions.find(q=>change.question_ids.includes(q.id)); prepare(q ? {...q.context, scientific_question:q.scientific_question, related_question_id:q.id, interaction_id:q.interaction_id, evidence_gap:q.evidence_gap, evidence:change.evidence} : {...state.context, evidence:change.evidence});}}>{t('Review → Prepare', '검토 → 준비')}<ArrowRight size={14}/></button></div>)}</>}
      {!intelligence && <div className="empty">{busy ? t('Checking scientific sources…', '과학적 출처 확인 중…') : t('No intelligence snapshot yet.', '인텔리전스 스냅샷이 아직 없습니다.')}</div>}
    </section>
    <section className="surface questions"><div className="eyebrow">{t('CONTINUE THE LOOP', '업무 흐름 이어가기')}</div><div className="section-heading"><h2>{t('Open scientific questions', '미해결 과학적 질문')}</h2><span className="count">{activeQuestions.length}</span></div>{state.questions.length ? state.questions.map(q => <article className="question-row" key={q.id}><div className="source-meta">{q.context.hcp || t('Synthetic interaction', '가상 교류')} · {q.context.disease}</div><h3>{q.scientific_question}</h3><small className="muted">{date(q.created_at, lang)}</small><div className="question-actions"><select aria-label={t('Question status', '질문 상태')} value={q.status} onChange={e => act(() => request(`/questions/${q.id}`, {status:e.target.value, follow_up_notes:q.follow_up_notes}, 'PATCH'))}>{[['OPEN','미해결'],['MONITOR','모니터링'],['FOLLOW-UP','후속 조치'],['RESOLVED','해결됨']].map(([v,k])=><option value={v} key={v}>{t(v,k)}</option>)}</select><button className="text-button" onClick={() => prepare({...q.context, scientific_question:q.scientific_question, related_question_id:q.id, interaction_id:q.interaction_id, evidence_gap:q.evidence_gap})}>{t('Prepare follow-up', '후속 준비')}<ArrowRight size={14}/></button></div><details><summary>{t('Follow-up notes', '후속 메모')}</summary><textarea aria-label={t('Follow-up notes', '후속 메모')} defaultValue={q.follow_up_notes} onBlur={e => act(() => request(`/questions/${q.id}`, {status:q.status, follow_up_notes:e.target.value}, 'PATCH'))}/></details></article>) : <div className="empty">{t('Questions raised in Capture return here for follow-up.', '기록에서 제기된 질문이 후속 조치를 위해 여기에 표시됩니다.')}</div>}</section></div>
  </>;
}
