import {useState} from 'react';
import {ArrowRight, Search, RefreshCw, BookMarked} from 'lucide-react';
import {request, date, basketItems, sourceKey} from './api';
import {PageHeading, Field, RecentPrepares, EvidenceList} from './components';
import ReportPanel from './ReportPanel';

export default function PreparePage({t, lang, state, reload, seed, onCapture, ensureGemini}) {
  const [context,setContext] = useState({...state.context,...(seed && !seed.prepare_id ? seed : {})});
  const [session,setSession] = useState(null);
  const [tab,setTab] = useState('evidence');
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [notice,setNotice] = useState('');
  const [versions,setVersions] = useState([]);
  const [historical,setHistorical] = useState(false);
  const [selectionOnly,setSelectionOnly] = useState(false);
  const [sourceFilter,setSourceFilter] = useState('all');
  const edit = (key,value) => setContext(c=>({...c,[key]:value}));
  async function open(id, revision=null) {
    setBusy(true); setError('');
    try {const s=await request(`/prepares/${id}${revision?`?revision=${revision}`:''}`); setSession(s); setContext(s.context); setHistorical(!!revision); setVersions(await request(`/prepares/${id}/versions`)); setTab('evidence'); setSourceFilter('all'); setSelectionOnly(false);} catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function search(refresh=false) {
    setBusy(true); setError(''); setNotice('');
    try {
      const related = session && session.context.hcp === context.hcp && session.context.disease === context.disease;
      const parent = refresh ? session?.id : related ? session.id : state.sessions.find(s=>context.hcp && s.context.hcp===context.hcp && s.context.disease===context.disease)?.id;
      const result=await request('/prepares',{context, parent_id:parent || null}); setSession(result); setHistorical(false); setVersions(await request(`/prepares/${result.id}/versions`)); setTab('evidence'); await reload();
    } catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function loadSample() {
    setBusy(true); setError(''); setNotice('');
    try {
      const s=await request('/samples/gsk-oncology',{});
      setSession(s); setContext(s.context); setHistorical(false); setTab('evidence'); setSourceFilter('all'); setSelectionOnly(true);
      setVersions(await request(`/prepares/${s.id}/versions`)); await reload();
      setNotice(t('GSK Jemperli vs MSD/Merck Keytruda sample saved. Real sources are selected in the basket; the HCP is fictional. Analyze with Gemini after configuring your key.', 'GSK Jemperli vs MSD/Merck Keytruda 샘플을 저장했습니다. 실제 출처를 바구니에 담았고 HCP는 가상입니다. 키 설정 후 Gemini로 분석하세요.'));
    } catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function run(path, custom) {
    setBusy(true); setError(''); setNotice('');
    if (['/analysis','/gaps','/signal-analysis'].includes(path)) {
      const configured = await ensureGemini(() => run(path,custom));
      if (!configured) {setBusy(false); return;}
    }
    try {if(custom) {await custom(); setNotice(t('Completed.', '완료되었습니다.'));} else {const s=await request(`/prepares/${session.id}${path}`, {language:lang, revision:session.revision}); setSession(s); setVersions(await request(`/prepares/${s.id}/versions`)); await reload();}} catch(e) {setError(path==='/analysis' ? t('AI analysis unavailable. Your evidence and session are saved. Retry when available. ', 'AI 분석을 이용할 수 없습니다. 근거와 세션은 저장되어 있습니다. 나중에 재시도하세요. ')+e.message : e.message);} finally {setBusy(false);}
  }
  async function toggle(key, category='evidence') {
    setBusy(true); setError('');
    try {
      const previous = category === 'evidence' ? session.selected_keys : session.selected_context?.[category] || [];
      const keys = previous.includes(key) ? previous.filter(k=>k!==key) : [...previous,key];
      const s=await request(`/prepares/${session.id}`, {revision:session.revision, selected_keys:category === 'evidence' ? keys : session.selected_keys, selected_context:{...session.selected_context, ...(category === 'evidence' ? {} : {[category]:keys})}}, 'PATCH');
      setSession(s); setVersions(await request(`/prepares/${s.id}/versions`)); await reload();
    } catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function changeTab(value) {setTab(value); if(value==='signals' && session.signals.status==='not_loaded' && !historical) await run('/signals');}
  const counts = session ? {evidence:session.evidence.length, treatment:session.treatment.length, signals:session.signals.status==='loaded' ? session.signals.items.length : null, gaps:session.gaps.length} : {};
  const shownEvidence = session?.evidence.filter(i=>(sourceFilter==='all'||i.source===sourceFilter) && (!selectionOnly || session.selected_keys.includes(sourceKey(i)))) || [];
  const contextChanged = session && ['hcp','disease','biomarker','setting','drugs','scientific_question'].some(k=>(session.context[k]||'')!==(context[k]||''));
  return <>
    <PageHeading eyebrow={t('BEFORE THE SCIENTIFIC EXCHANGE', '과학적 교류 전')} title={t('Prepare with perspective.', '과학적 맥락을 갖춘 준비.')} description={t('One question. Connected evidence. A considered scientific exchange.', '하나의 질문, 연결된 근거, 숙고된 과학적 교류.')}><RecentPrepares sessions={state.sessions} open={open} t={t} lang={lang}/></PageHeading>
    {error && <div className="notice error" role="alert">{error}</div>}{notice && <div className="notice success" role="status">{notice}</div>}
    <section className="surface sample-launch"><div><h2>{t('GSK Oncology comparison sample','GSK Oncology 비교 샘플')}</h2><p>{t('Jemperli (dostarlimab) vs Keytruda (pembrolizumab) · Endometrial cancer · RUBY / NRG-GY018','Jemperli(dostarlimab) vs Keytruda(pembrolizumab) · 자궁내막암 · RUBY / NRG-GY018')}</p></div><button className="secondary" disabled={busy} onClick={loadSample}>{t('Create sample & fill basket','샘플 생성 및 바구니 담기')}</button></section>
    <section className="surface context-form"><div className="section-heading"><h2>{t('HCP / meeting context', 'HCP / 미팅 맥락')}</h2><button className="text-button" disabled={busy} onClick={()=> {setContext({hcp:t('Demo thoracic oncologist', '데모 흉부 종양 전문의'),disease:'NSCLC',biomarker:'HER2',setting:'Previously treated advanced disease',scientific_question:t('What evidence informs HER2 treatment sequencing after prior systemic therapy?', '이전 전신 치료 후 HER2 치료 순서에 어떤 근거가 있나요?')}); setSession(null); setHistorical(false);}}>{t('Use synthetic scenario', '가상 시나리오 사용')}</button></div>
    <form onSubmit={e=>{e.preventDefault(); search();}}><div className="context-grid"><Field label={t('HCP · synthetic/demo', 'HCP · 가상/데모')} value={context.hcp} onChange={v=>edit('hcp',v)} placeholder={t('Demo HCP name', '데모 HCP 이름')}/><Field label={t('Disease / indication *', '질환 / 적응증 *')} value={context.disease} onChange={v=>edit('disease',v)} required placeholder="NSCLC"/><Field label={t('Biomarker', '바이오마커')} value={context.biomarker} onChange={v=>edit('biomarker',v)} placeholder={t('Optional', '선택 사항')}/><Field label={t('Setting', '치료 환경')} value={context.setting} onChange={v=>edit('setting',v)} placeholder={t('Optional', '선택 사항')}/></div><Field label={t('Drugs / comparison terms (comma-separated)','약제 / 비교 검색어 (쉼표로 구분)')} value={context.drugs} onChange={v=>edit('drugs',v)} placeholder="dostarlimab, pembrolizumab"/><Field label={t('Scientific question', '과학적 질문')} multiline value={context.scientific_question} onChange={v=>edit('scientific_question',v)} placeholder={t('What do you want to understand before this exchange?', '이번 교류 전에 무엇을 이해하고 싶으신가요?')}/>
    <div className="form-actions"><span className="muted small">{t('Use synthetic data only. Original source content stays in its source language.', '가상 데이터만 사용하세요. 출처 원문 언어는 유지됩니다.')}</span><div><button type="button" className="secondary" disabled={busy || !context.disease?.trim()} onClick={async()=> {setBusy(true); try{await request('/context',context,'PUT'); await reload(); setNotice(t('Therapeutic context saved.', '치료 영역 맥락이 저장되었습니다.'));}catch(e){setError(e.message);}finally{setBusy(false);}}}>{t('Save context', '맥락 저장')}</button><button className="primary" disabled={busy || !context.disease?.trim()}><Search size={16}/>{busy ? t('Working…', '처리 중…') : t('Search & prepare', '검색 및 준비')}</button></div></div></form></section>
    {seed?.evidence && !session && <section className="surface"><h2>{t('Evidence to review for your question', '질문 관련 검토 근거')}</h2><EvidenceList items={[seed.evidence]} t={t}/></section>}
    {!session ? <div className="prepare-empty"><BookMarked size={35}/><h2>{t('Start with the scientific question.', '과학적 질문에서 시작하세요.')}</h2><p>{t('Enter context once. Evidence, treatment, signals and review needs stay together in a saved preparation.', '맥락을 한 번 입력하세요. 근거, 치료, 신호와 검토 필요 사항이 하나의 준비 세션에 저장됩니다.')}</p><div className="workflow-steps"><span>{t('01 Context', '01 맥락')}</span><ArrowRight size={15}/><span>{t('02 Evidence', '02 근거')}</span><ArrowRight size={15}/><span>{t('03 Scientific exchange', '03 과학적 교류')}</span></div></div> : <>
      <div className="session-toolbar"><span>{t('Last searched', '최근 검색')}: {date(session.searched_at,lang)} · {t('Revision', '리비전')} {session.revision}</span><div><select disabled={busy} aria-label={t('Saved revisions', '저장된 리비전')} value={historical ? session.revision : ''} onChange={e=>open(session.id,e.target.value ? Number(e.target.value):null)}><option value="">{t('Current saved revision', '현재 저장된 리비전')}</option>{versions.map(v=><option value={v.revision} key={v.revision}>{t('Revision', '리비전')} {v.revision} · {date(v.saved_at,lang)}</option>)}</select><button className="secondary" disabled={busy} onClick={()=>search(true)}><RefreshCw size={14}/>{t('Refresh evidence · new version', '근거 갱신 · 새 버전')}</button></div></div>
      {historical && <p className="notice">{t('Historical snapshot. Reopen the current revision to edit; refresh creates a new linked session.', '과거 스냅샷입니다. 편집하려면 현재 리비전을 여세요. 갱신하면 연결된 새 세션이 생성됩니다.')}</p>}
      {contextChanged && <p className="notice">{t('Context edited. Displayed results belong to the saved context until you search again.', '맥락이 편집되었습니다. 다시 검색할 때까지 결과는 저장된 맥락에 해당합니다.')}</p>}
      {session.status!=='complete' && <p className="notice">{t('Search was interrupted or failed. The session is saved. Refresh evidence to retry.', '검색이 중단되거나 실패했습니다. 세션은 저장되어 있습니다. 근거를 갱신하여 재시도하세요.')}</p>}
      <div className="source-status">{Object.entries(session.source_status).map(([source,value])=><span className={`status ${value.status==='ok'?'':'failed'}`} key={source}>{source} · {value.status==='ok'?t('Available','연결됨'):t('Unavailable / timeout','이용 불가 / 시간 초과')}</span>)}</div>
      {session.sample && <p className="notice">{t('Curated sample with dated FDA summaries and retrieved publications/registries. Review source availability below. Independent trials are not head-to-head evidence; check current local labels and later updates.','날짜가 명시된 FDA 요약과 조회한 논문·시험 등록 자료로 구성한 샘플입니다. 아래 출처 연결 상태를 확인하세요. 별개 시험은 직접 비교 근거가 아닙니다. 최신 국내 허가사항과 후속 업데이트를 검토하세요.')}</p>}
      {session.comparison && <p className="notice">{session.comparison.newly_retrieved.length} {t('newly retrieved records', '새로 검색된 기록')} · {session.comparison.updated_records.length} {t('updated source records. This is not confirmed scientific change.', '변경된 출처 기록. 확인된 과학적 변화는 아닙니다.')}</p>}
      <section className="surface results"><div className="result-tabs" role="tablist">{[['evidence',t('EVIDENCE','근거')],['treatment',t('TREATMENT','치료')],['signals',t('SIGNALS','신호')],['gaps',t('GAPS','공백')]].map(([id,label])=><button disabled={busy} key={id} id={`tab-${id}`} role="tab" aria-selected={tab===id} aria-controls={`panel-${id}`} className={tab===id?'active':''} onClick={()=>changeTab(id)}>{label}<span>{counts[id]===null?'—':counts[id]}</span></button>)}</div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab==='evidence' && <><div className="result-tools"><span>{t('Counts show records saved in this session.', '건수는 이 세션에 저장된 기록 수입니다.')}</span><div><select aria-label={t('Filter source', '출처 필터')} value={sourceFilter} onChange={e=>setSourceFilter(e.target.value)}>{['all','PubMed','ClinicalTrials.gov','FDA','EMA'].map(s=><option key={s} value={s}>{s==='all'?t('All sources','모든 출처'):s}</option>)}</select><button className={selectionOnly?'text-button chosen':'text-button'} onClick={()=>setSelectionOnly(!selectionOnly)}>{t('Selected evidence only', '선택 근거만 보기')} {session.selected_keys.length}</button></div></div><EvidenceList items={shownEvidence} selected={session.selected_keys} onToggle={toggle} selectionDisabled={historical || busy} t={t}/></>}
        {tab==='treatment' && <><p className="notice">{t('FDA approved application / EMA authorised context. Review original indications for biomarker and setting eligibility. Trial registry records are shown in Evidence.', 'FDA 승인 신청 / EMA 허가 맥락입니다. 원문 적응증의 바이오마커 및 치료 환경 적합성을 검토하세요. 임상시험 기록은 근거에 표시됩니다.')}</p><EvidenceList items={session.treatment} selected={session.selected_context?.treatment || []} onToggle={key=>toggle(key,'treatment')} selectionDisabled={historical || busy} t={t} regulatory/></>}
        {tab==='signals' && <><p className="notice">{t('Public online discussion signals · Self-selected, hypothesis-generating, not representative or validated clinical evidence.', '공개 온라인 논의 신호 · 자기 선택된 가설 생성 자료이며 대표성 또는 검증된 임상 근거가 아닙니다.')}</p>{session.signals.status==='not_loaded'?<p className="empty">{t('Signals load once on first view and are saved to this session.', '신호는 처음 조회할 때 한 번 불러와 이 세션에 저장됩니다.')}</p>:session.signals.status==='unavailable'?<div className="empty">{t('Public signal source unavailable.', '공개 신호 출처를 이용할 수 없습니다.')}<button disabled={busy||historical} onClick={()=>run('/signals')}>{t('Retry', '재시도')}</button></div>:<><div className="source-status">{Object.entries(session.signals.source_status||{}).map(([s,v])=><span className="status" key={s}>{s} · {typeof v==='string' ? (v==='ok'?t('Available','연결됨'):t('Check source availability','출처 이용 가능 여부 확인')) : t('Check source availability','출처 이용 가능 여부 확인')}</span>)}</div><EvidenceList items={session.signals.items} selected={session.selected_context?.signals || []} onToggle={key=>toggle(key,'signals')} selectionDisabled={historical || busy} t={t}/></>}</>}
        {tab==='gaps' && <>
          <p className="notice">{t('Potential evidence gap — Medical review required. Derived review needs, not validated medical conclusions.', '잠재적 근거 공백 — 메디컬 검토 필요. 파생된 검토 필요 사항이며 검증된 의학적 결론이 아닙니다.')}</p>
          <button className="secondary" disabled={busy || historical || !session.selected_keys.length} onClick={() => run('/gaps')}>{t('Derive potential gaps · Gemini', '잠재적 공백 도출 · Gemini')}</button>
          {session.gaps.length ? session.gaps.map(g => <article className="gap-row" key={g.id}>
            <div className="evidence-row-top"><div className="eyebrow">{t('POTENTIAL REVIEW NEED', '잠재적 검토 필요 사항')}</div><button className="select-evidence" disabled={historical || busy} onClick={()=>toggle(String(g.id),'gaps')}>{session.selected_context?.gaps?.includes(String(g.id)) ? t('✓ Selected','✓ 선택됨') : t('+ Select','+ 선택')}</button></div><h3>{g.question}</h3>
            <p>{g.method === 'AI-derived interpretation' ? g.basis : t('Review whether the retrieved and selected evidence addresses this question. A limited search cannot establish that evidence is absent.', '조회 및 선택한 근거가 이 질문을 다루는지 검토하세요. 제한된 검색으로 근거의 부재를 입증할 수 없습니다.')}</p>
            <span className="micro-label">{g.method === 'AI-derived interpretation' ? t('AI-derived interpretation', 'AI 기반 해석') : t('Rule-derived review need', '규칙 기반 검토 필요 사항')}</span>
            {g.source_keys?.length > 0 && <details><summary>{t('Supporting source trace', '지원 출처 추적')}</summary><EvidenceList items={session.evidence.filter(i => g.source_keys.includes(sourceKey(i)))} t={t}/></details>}
          </article>) : <p className="empty">{t('No derived review needs. Enter a scientific question or review selected sources.', '도출된 검토 필요 사항이 없습니다. 과학적 질문을 입력하거나 선택된 근거를 검토하세요.')}</p>}
        </>}
      </div></section>
      <section className="surface basket-panel"><div className="section-heading"><h2>{t('Evidence basket', '근거 바구니')} · {basketItems(session).length}</h2><span className="micro-label">{t('Selected inputs for analysis', '분석에 사용할 선택 자료')}</span></div>
        {basketItems(session).length ? basketItems(session).map(({category,key,record})=><div className="basket-row" key={`${category}:${key}`}><span className="source-label">{{evidence:t('Evidence','근거'),treatment:t('Treatment','치료'),signals:t('Public signal','공개 신호'),gaps:t('Derived gap','파생 공백')}[category]}</span><span>{record.title || record.question || record.name || record.id}</span><button className="text-button" disabled={busy || historical} onClick={()=>toggle(key,category)} aria-label={t('Remove from basket','바구니에서 제거')}>{t('Remove','제거')}</button></div>) : <p className="empty-small">{t('Use + Select in any results tab to add analysis inputs.', '각 결과 탭의 + 선택으로 분석할 자료를 담으세요.')}</p>}
        <p className="muted small">{t('Analyze this basket below, then export the saved analysis to PDF or PPTX. Public signals and derived gaps retain their distinct status.', '아래에서 바구니를 분석한 뒤 저장된 분석을 PDF 또는 PPTX로 내보내세요. 공개 신호와 파생 공백은 구분하여 분석합니다.')}</p>
      </section>
      <ReportPanel {...{session,t,lang,busy,run,onCapture}} readOnly={historical}/>
    </>}
  </>;
}
