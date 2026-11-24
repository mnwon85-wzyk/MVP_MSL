import {forwardRef, useEffect, useImperativeHandle, useRef, useState} from 'react';
import {KeyRound, X} from 'lucide-react';
import {request} from './api';

const GeminiSettings = forwardRef(function GeminiSettings({t}, ref) {
  const [open,setOpen] = useState(false);
  const [key,setKey] = useState('');
  const [status,setStatus] = useState(null);
  const [busy,setBusy] = useState(false);
  const [message,setMessage] = useState('');
  const [error,setError] = useState(false);
  const pendingAnalysis = useRef(null);
  const [analysisPending,setAnalysisPending] = useState(false);
  useEffect(()=>{request('/gemini').then(setStatus).catch(()=>{});},[]);
  useImperativeHandle(ref, () => ({
    async ensureConfigured(resume) {
      setMessage(''); setError(false);
      try {
        const current = await request('/gemini');
        setStatus(current);
        if (current.configured) return true;
      } catch {
        setError(true);
        setMessage(t('Cannot check the Gemini configuration. Check the backend connection.', 'Gemini 설정을 확인할 수 없습니다. 백엔드 연결을 확인하세요.'));
      }
      pendingAnalysis.current = resume;
      setAnalysisPending(true);
      setOpen(true);
      return false;
    },
  }), [t]);
  function close() {if (!busy) {setOpen(false); setKey(''); setMessage(''); pendingAnalysis.current=null; setAnalysisPending(false);}}
  async function save(test=false) {
    setBusy(true); setMessage(''); setError(false);
    let resume = null;
    try {
      if (key.trim()) {setStatus(await request('/gemini',{api_key:key},'PUT')); setKey('');}
      if(test) {await request('/gemini/test',{}); setMessage(t('Gemini connection verified. You can now analyze your basket.', 'Gemini 연결을 확인했습니다. 이제 바구니를 분석할 수 있습니다.')); resume=pendingAnalysis.current; pendingAnalysis.current=null;}
      else setMessage(t('Key set for the running backend. Connection has not been tested.', '실행 중인 백엔드에 키를 설정했습니다. 연결은 아직 확인하지 않았습니다.'));
    } catch {setError(true); setMessage(t('Unable to configure or connect. Check your key, model access, quota, and backend connection.', '설정 또는 연결에 실패했습니다. 키, 모델 접근 권한, 사용량 한도와 백엔드 연결을 확인하세요.'));}
    finally {setBusy(false);}
    if(resume) {setOpen(false); setKey(''); setMessage(''); setAnalysisPending(false); await resume();}
  }
  return <><button className="gemini-settings-button" onClick={()=>{setOpen(true); request('/gemini').then(setStatus).catch(()=>{});}}><KeyRound size={15}/>{t('Gemini API key','Gemini API 키')}<span className={`key-status ${status?.configured ? 'configured' : ''}`}>{status?.configured ? t('Set','설정됨') : t('Not set','미설정')}</span></button>
    {open && <div className="modal-backdrop"><section className="surface key-dialog" role="dialog" aria-modal="true" aria-labelledby="gemini-dialog-title" onKeyDown={e=>{if(e.key==='Escape') close(); if(e.key==='Tab') {const controls=[...e.currentTarget.querySelectorAll('button:not(:disabled), input:not(:disabled), a[href]')]; const first=controls[0], last=controls[controls.length-1]; if(e.shiftKey && document.activeElement===first) {e.preventDefault(); last?.focus();} else if(!e.shiftKey && document.activeElement===last) {e.preventDefault(); first?.focus();}}}}><div className="section-heading"><h2 id="gemini-dialog-title">{t('Connect Gemini','Gemini 연결')}</h2><button aria-label={t('Close','닫기')} disabled={busy} onClick={close}><X size={18}/></button></div>
      {analysisPending && <p className="notice">{t('A Gemini API key is required for this analysis. After a successful connection test, your requested analysis will run automatically.', '이 분석에는 Gemini API 키가 필요합니다. 키를 입력하고 연결 확인에 성공하면 요청한 분석을 자동으로 실행합니다.')}</p>}
      <p>{t('Enter your Google AI Studio API key. The key is sent only to your local backend; Gemini requests are made by the backend.', 'Google AI Studio API 키를 입력하세요. 키는 로컬 백엔드로 전달되고, Gemini 요청은 백엔드에서 실행합니다.')}</p>
      <label className="field"><span>Gemini API key</span><input autoFocus type="password" autoComplete="off" value={key} onChange={e=>setKey(e.target.value)} placeholder={status?.configured ? t('Enter a replacement key','변경할 키 입력') : 'AIza…'} disabled={busy}/></label>
      <p className="muted small">{t('Stored only in the running backend process. It is not written to browser storage or the database. Enter it again after a backend restart.', '실행 중인 백엔드 메모리에만 설정됩니다. 브라우저 저장소나 DB에 기록하지 않습니다. 백엔드 재시작 후에는 다시 입력하세요.')}</p>
      <p className="small">{t('Model','모델')}: {status?.model || '—'} · <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">{t('Get an API key','API 키 발급')}</a></p>
      {message && <p role={error?'alert':'status'} className={`notice ${error?'error':'success'}`}>{message}</p>}
      <div className="output-actions"><button className="primary" disabled={busy || (!key.trim() && !status?.configured)} onClick={()=>save(true)}>{busy ? t('Connecting…','연결 중…') : t('Save & test connection','설정 및 연결 확인')}</button><button disabled={busy || !key.trim()} onClick={()=>save(false)}>{t('Set key only','키만 설정')}</button><button disabled={busy} onClick={close}>{t('Done','완료')}</button></div>
    </section></div>}
  </>;
});
export default GeminiSettings;
