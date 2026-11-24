import {useEffect, useState, useCallback, useRef} from 'react';
import {LayoutDashboard, BookOpen, MessageSquare, ArrowUpRight, FlaskConical} from 'lucide-react';
import {request} from './api';
import DashboardPage from './DashboardPage';
import PreparePage from './PreparePage';
import CapturePage from './CapturePage';
import GeminiSettings from './GeminiSettings';
import CvrmPage from '../cvrm/CvrmPage';
import './workflow.css';

export default function WorkflowApp() {
  const [lang, setLang] = useState(() => localStorage.getItem('msl-language') || 'kr');
  const [page, setPage] = useState('cvrm');
  const [seed, setSeed] = useState(null);
  const [state, setState] = useState(null);
  const [error, setError] = useState('');
  const geminiSettings = useRef(null);
  const ensureGemini = resume => geminiSettings.current.ensureConfigured(resume);
  const t = (en, kr) => lang === 'kr' ? kr : en;
  const reload = useCallback(async () => { try {setState(await request('/state')); setError('');} catch (e) {setError(e.message);} }, []);
  useEffect(() => {void request('/state').then(setState).catch(() => reload());}, [reload]);
  useEffect(() => {localStorage.setItem('msl-language', lang); document.documentElement.lang = lang === 'kr' ? 'ko' : 'en';}, [lang]);
  function prepare(context = null) {setSeed(context ? {...context, nonce: Date.now()} : null); setPage('prepare');}
  const menus = [['cvrm', FlaskConical, t('CVRM PORTFOLIO', 'CVRM 포트폴리오')], ['dashboard', LayoutDashboard, t('DASHBOARD', '대시보드')], ['prepare', BookOpen, t('LIVE SEARCH / PREPARE', '실시간 검색 / 준비')], ['capture', MessageSquare, t('CAPTURE', '기록')]];
  const openLegacy = useCallback(() => setPage('dashboard'), []);
  if (page === 'cvrm') return <CvrmPage lang={lang} onLegacy={openLegacy}/>;
  return <div className="workflow-app">
    <aside className="rail"><div className="brand-name">MSL ONE</div><nav aria-label={t('Primary navigation', '주 탐색')}>{menus.map(([id, Icon, label]) => <button key={id} className={page === id ? 'nav-item active' : 'nav-item'} onClick={() => setPage(id)}><Icon size={19}/>{label}<span>0{menus.findIndex(m => m[0] === id) + 1}</span></button>)}</nav>
      <div className="rail-bottom"><FlaskConical size={20}/><p>{t('Independent portfolio MVP', '독립 포트폴리오 MVP')}</p><small>{t('Synthetic interactions only. No patient or confidential company data.', '가상 교류 데이터만 입력하세요. 환자 정보 및 회사 기밀 입력 금지.')}</small><div className="loop-label">{t('Prepare → Capture → Follow-up', '준비 → 기록 → 후속 조치')}</div></div>
    </aside>
    <div className="workspace"><header className="topbar"><span>{t('FIELD MEDICAL / SCIENTIFIC WORKSPACE', '필드 메디컬 / 과학적 업무 공간')}</span><div className="topbar-actions"><GeminiSettings ref={geminiSettings} t={t}/><div className="language-switch" aria-label={t('Language', '언어')}>{['kr','en'].map(l => <button key={l} aria-pressed={lang === l} className={lang === l ? 'active' : ''} onClick={() => setLang(l)}>{l.toUpperCase()}</button>)}</div></div></header>
      <main>{error && page !== 'cvrm' && <div className="notice error" role="alert">{t('Cannot connect to the backend. Start api:app on port 8000. ', '백엔드 연결 실패. api:app을 8000 포트에서 실행하세요. ')}{error}<button onClick={reload}>{t('Retry', '재시도')}</button></div>}
      {page === 'cvrm' ? <CvrmPage lang={lang}/> : !state ? <div className="empty">{t('Connecting to your saved workspace…', '저장된 업무 공간에 연결 중…')}</div> : page === 'dashboard' ? <DashboardPage {...{t, lang, state, reload, prepare}}/> : page === 'prepare' ? <PreparePage key={seed?.nonce || 'prepare'} {...{t, lang, state, reload, seed, ensureGemini}} onCapture={id => {setSeed({prepare_id:id}); setPage('capture');}}/> : <CapturePage {...{t, lang, state, reload, prepare, seed}}/>}</main>
      <footer>{t('Scientific workflow prototype · Medical review required · Not medical advice', '과학적 업무 흐름 프로토타입 · 메디컬 검토 필요 · 의학적 조언 아님')}<ArrowUpRight size={14}/></footer>
    </div>
  </div>;
}
