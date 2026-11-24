// Domain-term counts are local text statistics, not inferred clinical demand.
export const captureTerms=[
 {label:'칼륨·모니터링',pattern:'고칼륨혈증|칼륨|hyperkal\\w*|potassium|모니터링|monitoring',query:'potassium monitoring'},
 {label:'신기능·CKD',pattern:'신기능|콩팥|신장|만성콩팥병|eGFR|CKD|kidney',query:'chronic kidney disease'},
 {label:'알부민뇨',pattern:'알부민뇨|단백뇨|UACR|albuminuria',query:'albuminuria'},
 {label:'심부전',pattern:'심부전|heart failure|HFpEF|HFrEF',query:'heart failure'},
 {label:'안전성·부작용',pattern:'안전성|부작용|출혈|safety|adverse|bleeding',query:'safety'},
 {label:'치료 효과',pattern:'효과|유효성|결과|efficacy|outcome',query:'efficacy'},
 {label:'환자 부담·접근성',pattern:'부담|비용|급여|접근성|삶의 질|quality of life|access',query:'quality of life'},
 {label:'병용 치료',pattern:'병용|SGLT.?2|엠파글리플로진|empagliflozin|combination',query:'combination therapy'}
];
export function captureKeywords(text){return captureTerms.map(term=>({label:term.label,count:(String(text).match(new RegExp(term.pattern,'giu'))||[]).length,query:term.query})).filter(x=>x.count).sort((a,b)=>b.count-a.count);}
export function captureQuery(text,product='finerenone'){const terms=captureKeywords(text).slice(0,3).map(x=>x.query);return [product,...terms].join(' AND ');}
export function createSpeechCapture({Recognition,onText,onState,initialText=''}){
 if(!Recognition)return {supported:false,start(){onState('unsupported');},stop(){},dispose(){}};
 const recognition=new Recognition();recognition.lang='ko-KR';recognition.continuous=true;recognition.interimResults=true;recognition.maxAlternatives=1;
 let wanted=false,disposed=false,failed=false,base=initialText,latest=initialText,restart;
 recognition.onstart=()=>onState('listening');
 recognition.onresult=event=>{const finals=[],interim=[];for(let i=0;i<event.results.length;i++){const result=event.results[i];(result.isFinal?finals:interim).push(result[0].transcript);}latest=[base,...finals].filter(Boolean).join(' ').slice(0,20000);onText({final:latest,interim:interim.join(' ')});};
 recognition.onerror=event=>{if(event.error==='no-speech')return;wanted=false;failed=true;onState(event.error||'error');};
 recognition.onend=()=>{base=latest;if(wanted&&!disposed){restart=setTimeout(()=>{try{recognition.start();}catch{wanted=false;onState('error');}},400);}else if(!disposed&&!failed)onState('idle');};
 return {supported:true,start(){if(wanted||disposed)return;wanted=true;failed=false;onState('starting');try{recognition.start();}catch{wanted=false;onState('error');}},stop(){wanted=false;failed=false;clearTimeout(restart);try{recognition.stop();}catch{}onState('idle');},dispose(){disposed=true;wanted=false;clearTimeout(restart);recognition.onend=null;recognition.onresult=null;recognition.onerror=null;try{recognition.abort();}catch{}}};
}
