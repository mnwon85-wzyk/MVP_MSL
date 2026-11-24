export const headlines = [
 {id:'N01',category:'Bayer',publisher:'Bayer US',date:'2026-11-04',title:'Bayer, AHA 2026 심혈관·신장·뇌졸중 연구 발표 안내',url:'https://www.bayer.com/en-us/united-states/news-and-stories/2026/aha-sessions',summary:'11월 6~9일 AHA에서 다룰 finerenone과 asundexian 연구 발표를 안내한 보도자료입니다. 발표 예고와 결과 논문을 구분해 확인하세요.',check:'학회 발표의 원 논문과 분석 설계를 확인',source:'확인한 공식 보도자료'},
 {id:'N02',category:'Bayer',publisher:'Bayer',date:'2026-10-08',title:'비당뇨 CKD finerenone 적응증 확대 신청, 미국 FDA 접수',url:'https://www.bayer.com/media/en-us/us-fda-accepts-bayers-supplemental-new-drug-application-for-finerenone-in-chronic-kidney-disease-without-diabetes/',summary:'Bayer가 FIND-CKD에 근거한 미국 sNDA 접수를 발표했습니다. 신청 접수는 승인과 다릅니다. 국내 허가와 급여는 별도로 확인해야 합니다.',check:'규제 단계와 대상 국가를 구분',source:'확인한 공식 보도자료'},
 {id:'N03',category:'CV',publisher:'ESC',date:'2026-08-30',title:'심혈관질환과 만성콩팥병을 함께 다룬 ESC 가이드라인 소식',url:'https://www.escardio.org/news/news-room/congress-news/',summary:'ESC Congress News에 CVD와 CKD 가이드라인 소개가 게시되어 있습니다. 적용 대상과 권고 문구는 정식 가이드라인에서 확인하세요.',check:'가이드라인 원문·권고 수준 확인',source:'확인한 학회 뉴스 목록'},
 {id:'N04',category:'CV',publisher:'ESC',date:'2026-11-13',title:'심부전 모바일 앱·원격 모니터링 관련 새 학회 소식',url:'https://www.escardio.org/news/press/press-releases',summary:'11월 13일 ESC 보도자료 목록에 원격 모니터링과 심부전 증상·삶의 질 연구 소식이 올라왔습니다. 제목만으로 임상 효과를 확정하지 않습니다.',check:'연구 대상·비교군·환자보고결과 확인',source:'학회 목록 제목 확인'}
];
export const hcps = [
 {id:'kim',name:'김성균',english:'SungGyun Kim',hospital:'한림대학교성심병원',department:'신장내과',product:'finerenone',authorQuery:'(Kim SG[Author] OR Kim SungGyun[Author]) AND finerenone',ids:['E02'],news:[{title:'케렌디아 런천 심포지엄 발표 보도',date:'2024-06-18',url:'https://www.bokuennews.com/news/article.html?no=245549',summary:'APCN&KSN 2024 런천 심포지엄에서 알부민뇨 진단에 관해 발표한 이력이 보도되었습니다.'},{title:'RAS, SGLT-2, 그리고 케렌디아의 등장',date:'2023-04-03',url:'https://www.khidi.or.kr/board/view?linkId=48892835&menuId=MENU01816',summary:'KHIDI에 게재된 좌담회 기사에서 소속과 CKD 관련 논의 주제를 확인할 수 있습니다.'}],interests:['알부민뇨 평가','당뇨병 동반 CKD','신기능 추적'],relationship:'공개 기사에 Bayer 제품 심포지엄 발표 이력. 공식 KOL 지정 여부는 확인되지 않음.',affiliationDate:'기사 2024 / 논문 소속 2026; 현 소속은 방문 전 재확인'},
 {id:'jung',name:'정성진',english:'영문 저자명 확인 필요',hospital:'가톨릭대학교 여의도성모병원',department:'신장내과',product:'finerenone',authorQuery:'',ids:[],news:[{title:'RAS, SGLT-2, 그리고 케렌디아의 등장',date:'2023-04-03',url:'https://www.khidi.or.kr/board/view?linkId=48892835&menuId=MENU01816',summary:'CKD 치료와 케렌디아를 주제로 한 좌담회 참여 기사입니다. 영문 저자명과 동명이인 여부는 원문 소속으로 확인해야 합니다.'}],interests:['CKD 치료 옵션','RAS / SGLT-2 근거'],relationship:'제품 관련 공개 좌담회 참여 이력. Bayer KOL 지정 여부는 확인되지 않음.',affiliationDate:'2023년 기사 소속; 현 소속과 영문 저자명은 재확인'}
];
export const searchExamples = [
 {label:'피네레논 · 당뇨병과 CKD',query:'finerenone AND (diabetes OR chronic kidney disease)',trials:'finerenone'},
 {label:'김성균 교수 · 피네레논 논문',query:'(Kim SG[Author] OR Kim SungGyun[Author]) AND finerenone',trials:'finerenone'},
 {label:'한국 AF · 리바록사반',query:'rivaroxaban AND Korea AND atrial fibrillation',trials:'rivaroxaban atrial fibrillation'},
 {label:'심부전 · 베리시구앗',query:'vericiguat AND heart failure',trials:'vericiguat heart failure'}
];
export const questionPrompts = ['이 치료의 최신 근거는 뭐지?','HCP가 물어볼 만한 포인트는 뭐지?','환자들이 실제로 어려워하는 건 논문에서 다뤄졌나?','이 gap이 discussion point가 될 수 있나?'];
export const topics = ['효과 / 결과','안전성 / 모니터링','환자 경험 / 접근성','근거 적용 / gap','기타'];
export const companyContext = [
 {id:'C01',scope:'글로벌 · 전사',title:'myGenAssist와 사내 AI 활용',date:'2026-11-14 확인',url:'https://www.bayer.com/en/about-us/innovation/unleashing-the-potential-of-ai',finding:'공식 페이지는 myGenAssist를 4만 명 넘는 직원에게 제공하고 사내 애플리케이션용 API도 운영한다고 설명합니다.',limit:'한국 의학부의 접근 권한·사용률·특정 도구 도입을 확인하는 자료는 아닙니다.'},
 {id:'C02',scope:'프랑스 · 약물감시',title:'문서 작성 업무의 myGenAssist 연구',date:'2025-03-10',url:'https://www.jmir.org/2025/1/e65651/',finding:'문서 보완 요청 작성 업무를 4개월간 평가한 연구에서 보정된 평균 시간 절감은 23.3% (95% CI 13.8–32.8%)였습니다. 응답률의 유의한 차이는 없었습니다.',limit:'한국 MSL 업무나 MSL ONE의 생산성 수치로 일반화하지 않습니다.'},
 {id:'C03',scope:'미국 행사 안내 · Medical',title:'메디컬 인사이트를 실행으로 연결하는 사례',date:'2026-05-14',url:'https://www.veeva.com/kr/resources/veeva-commercial-summit-to-feature-biopharmas-ai-successes-and-the-path-to-agentic-commercial/',finding:'Veeva의 서밋 안내에는 Bayer의 실행으로 이어지는 메디컬 인사이트 포착·공유 사례가 포함돼 있습니다.',limit:'한국 CVRM팀의 도입 또는 특정 AI 기능 사용을 증명하지는 않습니다.'},
 {id:'C04',scope:'한국 · 오픈이노베이션',title:'Co.Lab Connect Seoul',date:'2026-10-15',url:'https://www.bayer.com/ko-kr/korea/bayer-korea-news/20261015',finding:'공식 발표는 AI 신약개발을 포함한 국내 초기 스타트업을 글로벌 전문가·파트너와 연결하는 프로그램을 설명합니다.',limit:'직원용 AI 서비스나 한국 의학부의 업무 시스템과는 별개입니다.'},
 {id:'C05',scope:'글로벌 담당자 인터뷰',title:'HCP에게 필요한 짧고 임상적인 콘텐츠',date:'2025년 인터뷰 · 2026-11-14 확인',url:'https://www.emjreviews.com/emj-gold/article/medical-affairs-whats-working-for-hcps-in-2025/',finding:'Bayer 글로벌 메디컬 커뮤니케이션 담당자는 상호작용형 학습과 임상 현장에 필요한 짧은 콘텐츠를 설명했습니다.',limit:'담당자 인터뷰에 근거한 방향이며 한국 조직의 도입 현황은 아닙니다.'}
];
