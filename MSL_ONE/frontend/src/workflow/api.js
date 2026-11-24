export const API = import.meta.env.VITE_API_BASE || 'http://localhost:8000';
export async function request(path, data, method = data === undefined ? 'GET' : 'POST') {
  const response = await fetch(`${API}/workflow${path}`, {method, headers: {'Content-Type': 'application/json'}, ...(data === undefined ? {} : {body: JSON.stringify(data)})});
  if (!response.ok) { let error; try { error = await response.json(); } catch { error = {}; } throw new Error(error.detail || `HTTP ${response.status}`); }
  return response.json();
}
export function download(text, filename, type = 'text/plain') {
  const url = URL.createObjectURL(new Blob([text], {type}));
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export const sourceKey = item => `${item.source}:${item.id || item.pmid || item.url || item.title}`;
export const text = value => typeof value === 'object' ? JSON.stringify(value) : String(value || '');
export const date = (value, lang) => value ? new Date(value).toLocaleString(lang === 'kr' ? 'ko-KR' : 'en-GB', {timeZone: 'Asia/Seoul', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'}) : '—';

export function basketItems(session) {
  return ['evidence','treatment','signals','gaps'].flatMap(category => {
    const records = category === 'signals' ? session.signals.items || [] : session[category] || [];
    const keys = category === 'evidence' ? session.selected_keys : session.selected_context?.[category] || [];
    return records.filter(i => keys.includes(category === 'gaps' ? String(i.id) : sourceKey(i))).map(record => ({category, key:category === 'gaps' ? String(record.id) : sourceKey(record), record}));
  });
}
