import {readFileSync,writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
const input=new URL('../portfolio/MSL_ONE_CVRM_MVP.html',import.meta.url);
const output=new URL('../sites/msl-one-portfolio/page.html',import.meta.url);
let html=readFileSync(input,'utf8');
const localOrigin="const origin=typeof location!=='undefined'&&/^https?:$/.test(location.protocol)&&location.port==='8000'?'':'http://127.0.0.1:8000';";
if(!html.includes(localOrigin))throw Error('Review the API origin contract before publishing.');
html=html.replace(localOrigin,"const origin='';")
 .replaceAll('LOCAL · PRIVATE','PUBLIC DEMO')
 .replaceAll("'msl-cvrm-v2'","'msl-cvrm-public-v1'")
 .replaceAll('API 키는 이 브라우저 세션에 연결된 서버 메모리에만 보관하며, 연결은 1시간 후 만료됩니다. 브라우저 저장소·DB에는 저장하지 않습니다.','API 키는 암호화된 HttpOnly 세션 쿠키로 연결되며 1시간 후 만료됩니다. 브라우저 스크립트·로컬 저장소·DB에 평문 키를 저장하지 않습니다.')
 .replaceAll('로컬 API 실행 상태와 인터넷 연결','공개 검색 서비스와 인터넷 연결')
 .replaceAll('로컬 API와 인터넷 연결','공개 검색 서비스와 인터넷 연결')
 .replaceAll('로컬 API를 통해 실제 검색합니다.','공개 서버를 통해 실제 검색합니다.')
 .replaceAll('공개 근거 + 연습 기록 · 의학적 조언 아님','공개 포트폴리오 · 기록은 방문자 브라우저에만 저장 · 의학적 조언 아님');
writeFileSync(output,html);
console.log('Prepared public demo:',fileURLToPath(output));
