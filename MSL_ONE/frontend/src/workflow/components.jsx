import {ArrowUpRight, Check, FileText} from 'lucide-react';
import {date, sourceKey, text} from './api';

export function PageHeading({eyebrow, title, description, children}) {
  return <div className="page-heading"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{children}</div>;
}
export function Field({label, value, onChange, multiline=false, ...props}) {
  const Tag = multiline ? 'textarea' : 'input';
  return <label className="field"><span>{label}</span><Tag value={value || ''} onChange={e => onChange(e.target.value)} {...props}/></label>;
}
export function EvidenceList({items, selected=[], onToggle, t, regulatory=false, selectionDisabled=false}) {
  if (!items.length) return <div className="empty"><FileText size={28}/><p>{t('No results returned. Check source status or refine your context.', '반환된 결과가 없습니다. 출처 상태를 확인하거나 맥락을 조정하세요.')}</p></div>;
  return <div className="evidence-list">{items.map((item, n) => {
    const key = sourceKey(item); const chosen = selected.includes(key);
    const url = item.url || item.medicine_url || item.source_url;
    const validUrl = /^https?:\/\//i.test(url || '') ? url : null;
    return <article key={key || n} className={`evidence-row ${chosen ? 'selected' : ''}`}><div className="evidence-row-top"><div className="source-meta"><span className="source-label">{item.source}</span><span>{text(item.source_date || item.updated_date || item.date || item.published_at)}</span><span>{item.id}</span></div>{onToggle && <button className={`select-evidence ${chosen ? 'chosen' : ''}`} disabled={selectionDisabled} onClick={() => onToggle(key)}>{chosen ? <Check size={14}/> : '+'}{chosen ? t('Selected', '선택됨') : t('Select', '선택')}</button>}</div>
      <h3>{validUrl ? <a href={validUrl} target="_blank" rel="noreferrer">{text(item.title || item.name || item.id)}<ArrowUpRight size={16}/></a> : text(item.title || item.name || item.id)}</h3>
      {item.source === 'ClinicalTrials.gov' && <div className="micro-label">{t('Trial registry · Not proof of approval', '임상시험 등록 · 승인 증거 아님')}</div>}
      {regulatory && <div className="micro-label">{t('Approved regulatory record · Verify biomarker / setting eligibility', '승인 규제 기록 · 바이오마커 / 치료 환경 적합성 확인 필요')}</div>}
      {(item.abstract || item.summary || item.body || item.text || item.description || item.content || item.indications || item.therapeutic_indication) && <details><summary>{regulatory ? t('Original indication text', '규제 적응증 원문') : t('Original source text', '출처 원문')}</summary><p className="source-text">{text(regulatory ? item.indications || item.therapeutic_indication : item.abstract || item.summary || item.body || item.text || item.description || item.content || item.indications)}</p></details>}
    </article>;
  })}</div>;
}
export function RecentPrepares({sessions, open, t, lang}) {
  return <details className="history"><summary>{t('Recent prepares', '최근 준비')}<span>{sessions.length}</span></summary><div className="history-list">{sessions.length ? sessions.slice(0,30).map(s => <button key={s.id} onClick={e => {open(s.id); e.currentTarget.closest('details').open = false;}}><strong>{s.context.hcp || t('Scientific preparation', '과학적 준비')}</strong><span>{s.context.disease} {s.context.biomarker && `· ${s.context.biomarker}`}</span><small>{date(s.created_at, lang)}</small></button>) : <p>{t('Your saved sessions will appear here.', '저장된 세션이 여기에 표시됩니다.')}</p>}</div></details>;
}
