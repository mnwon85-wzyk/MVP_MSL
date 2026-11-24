"""Public-source retrieval for the CVRM workspace. No HCP relationship inference."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import html
import re
import time
import xml.etree.ElementTree as ET
from urllib.parse import urlencode, urlparse
import requests
from fastapi import APIRouter, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, SecretStr
from services.pubmed import search_pubmed_paginated
from services.clinicaltrials import search_trials_paginated
from services.news_article import article_summary
from services import question_analysis

router = APIRouter(prefix='/cvrm')
_news_cache = {}

def now():
    return datetime.now(timezone.utc).isoformat()

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=700)
    trial_query: str = Field(default='', max_length=700)
    page: int = Field(default=1, ge=1, le=10)

class NewsRequest(BaseModel):
    query: str = Field(default='(Bayer OR 바이엘) (finerenone OR Kerendia OR cardiovascular OR 심혈관) when:30d', min_length=1, max_length=500)
    refresh: bool = False

class ArticleRequest(BaseModel):
    url: str = Field(min_length=10, max_length=4096)

class LlmConnection(BaseModel):
    api_key: SecretStr
    model: str = Field(min_length=1, max_length=100, pattern=r'^[A-Za-z0-9._:-]+$')

class QuestionRequest(BaseModel):
    question: str = Field(default='', max_length=4000)
    transcript: str = Field(default='', max_length=20000)
    include_transcript: bool = False
    query: str = Field(default='finerenone', min_length=1, max_length=700)

def source_result(fn, query, page):
    try:
        value = fn(query, page=page, page_size=12)
        return {'status':'ok', 'items':value['items'], 'total':value['total'], 'query':query, 'page':page}
    except Exception as exc:
        # Preserve failure state; never manufacture search records.
        return {'status':'unavailable', 'items':[], 'total':None, 'query':query, 'page':page, 'error':type(exc).__name__}

def search_public(payload):
    with ThreadPoolExecutor(max_workers=2) as pool:
        papers = pool.submit(source_result, search_pubmed_paginated, payload.query, payload.page)
        trials = pool.submit(source_result, search_trials_paginated, payload.trial_query or payload.query, payload.page)
        return {'papers':papers.result(), 'trials':trials.result(), 'retrieved_at':now(), 'method':'Public database retrieval; not a systematic review'}

def plain(text):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]*>', ' ', text or ''))).strip()

def search_news(query, refresh=False):
    cached = _news_cache.get(query)
    if cached and not refresh and time.monotonic() - cached[0] < 1800:
        return {**cached[1], 'cached':True}
    feed = 'https://news.google.com/rss/search?' + urlencode({'q':query,'hl':'ko','gl':'KR','ceid':'KR:ko'})
    try:
        response = requests.get(feed, timeout=18)
        response.raise_for_status()
        root = ET.fromstring(response.content[:2_000_000])
        items = []
        for item in root.findall('./channel/item')[:12]:
            url = item.findtext('link', '')
            if urlparse(url).scheme not in ('http','https'):
                continue
            items.append({'id':item.findtext('guid') or url,'title':plain(item.findtext('title')), 'url':url, 'date':item.findtext('pubDate',''), 'publisher':plain(item.findtext('source')), 'summary':plain(item.findtext('description'))[:500], 'source':'Google News RSS', 'access':'RSS title/excerpt only; original article not reviewed'})
        result = {'status':'ok', 'items':items, 'query':query, 'retrieved_at':now(), 'cached':False}
        _news_cache[query]=(time.monotonic(),result)
        if len(_news_cache)>50:
            _news_cache.pop(next(iter(_news_cache)))
        return result
    except Exception as exc:
        return {'status':'unavailable','items':[], 'query':query, 'retrieved_at':now(), 'error':type(exc).__name__, 'cached':False}

@router.get('')
def workspace():
    return FileResponse(Path(__file__).parent/'portfolio/MSL_ONE_CVRM_MVP.html')

@router.get('/health')
def health():
    return {'status':'ok','time':now()}

@router.post('/search')
def search(payload: SearchRequest):
    return search_public(payload)

@router.post('/news')
def news(payload: NewsRequest):
    return search_news(payload.query, payload.refresh)

@router.post('/news/article')
def news_article(payload: ArticleRequest):
    return article_summary(payload.url)

@router.post('/llm/connect')
def llm_connect(payload: LlmConnection, request: Request, response: Response):
    if not 15 <= len(payload.api_key.get_secret_value()) <= 300:
        return {'status':'unavailable','configured':False,'message':'OpenAI API 키 형식을 확인하세요.'}
    previous = request.cookies.get('msl_llm')
    token = question_analysis.connect(payload.api_key.get_secret_value(), payload.model)
    if previous:
        question_analysis.disconnect(previous)
    response.set_cookie('msl_llm', token, httponly=True, secure=request.url.scheme=='https', samesite='strict', path='/cvrm', max_age=3600)
    return {'status':'ok', 'configured':True, 'model':payload.model, 'verified':False}

@router.post('/llm/status')
def llm_status(request: Request):
    return question_analysis.settings(request.cookies.get('msl_llm'))

@router.post('/llm/disconnect')
def llm_disconnect(request: Request, response: Response):
    question_analysis.disconnect(request.cookies.get('msl_llm'))
    response.delete_cookie('msl_llm', path='/cvrm')
    return {'configured':False}

@router.post('/question/analyze')
def question_analyze(payload: QuestionRequest, request: Request):
    return question_analysis.analyze(request.cookies.get('msl_llm'), payload.question, payload.transcript, payload.include_transcript, payload.query)

@router.post('/review')
def review(payload: SearchRequest):
    with ThreadPoolExecutor(max_workers=2) as pool:
        evidence_future=pool.submit(search_public,payload)
        news_future=pool.submit(search_news,(payload.trial_query or payload.query)[:400])
        evidence=evidence_future.result()
        news_result=news_future.result()
    return {**evidence, 'news':news_result, 'analysis':{
        'method':'Retrieved abstracts / registry summaries grouped for human review. No treatment recommendation or generated clinical conclusion.',
        'next_steps':['Check whether the population and endpoints address the question.','Read the full text, safety findings and conflicting evidence.','Record interpretation separately from the original HCP question.']}}


class PreparationFile(BaseModel):
    name: str = Field(max_length=180)
    text: str = Field(max_length=20000)

class PreparationRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    query: str = Field(min_length=1, max_length=700)
    news_query: str = Field(min_length=1, max_length=500)
    files: list[PreparationFile] = Field(default_factory=list, max_length=3)
    use_llm: bool = False

@router.post('/preparation')
def preparation(payload: PreparationRequest, request: Request):
    from services.preparation import answer
    with ThreadPoolExecutor(max_workers=2) as pool:
        paper_future=pool.submit(source_result, search_pubmed_paginated, payload.query, 1)
        news_future=pool.submit(search_news, payload.news_query)
        papers, articles=paper_future.result(),news_future.result()
    papers['items']=papers['items'][:4]
    articles['items']=articles['items'][:4]
    context=[{'id':'P'+str(i+1),'title':p.get('title',''),'text':p.get('abstract','')[:2200]} for i,p in enumerate(papers['items'])]
    context += [{'id':'N'+str(i+1),'title':p['title'],'text':p['summary'],'scope':'RSS excerpt only'} for i,p in enumerate(articles['items'])]
    ai=answer(request.cookies.get('msl_llm'),payload.question,context,[f.model_dump() for f in payload.files]) if payload.use_llm else {'status':'not_requested','message':'통합 답변·예상 질문은 LLM으로 답변 준비를 누르세요.'}
    return {'papers':papers,'news':articles,'ai':ai,'question':payload.question,'retrieved_at':now()}


class PreparationUpload(BaseModel):
    name: str = Field(max_length=180)
    base64: str = Field(max_length=7000000)

@router.post('/preparation/file')
def preparation_file(payload: PreparationUpload):
    import base64
    import io
    import zipfile
    try:
        raw=base64.b64decode(payload.base64, validate=True)
        if len(raw)>5*1024*1024:
            raise ValueError('File too large')
        ext=Path(payload.name).suffix.lower()
        if ext in ('.txt','.md'):
            text=raw.decode('utf-8-sig')
        elif ext=='.pdf':
            from pypdf import PdfReader
            reader=PdfReader(io.BytesIO(raw))
            if reader.is_encrypted or len(reader.pages)>100:
                raise ValueError('PDF limit')
            text='\n'.join((page.extract_text() or '')[:20000] for page in reader.pages[:30])
        elif ext=='.docx':
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                info=archive.getinfo('word/document.xml')
                if info.file_size>5000000:
                    raise ValueError('Document limit')
                root=ET.fromstring(archive.read(info))
                text=' '.join(root.itertext())
        else:
            raise ValueError('Unsupported file')
        text=text.strip()[:20000]
        if not text:
            raise ValueError('No text')
        return {'status':'ok','text':text,'scope':'최대 20,000자 발췌 · PDF 최대 30페이지'}
    except Exception:
        return {'status':'unavailable','message':'텍스트 추출 실패: UTF-8 TXT/MD, 일반 DOCX 또는 텍스트 PDF를 사용하세요. 암호화·이미지 PDF는 지원하지 않습니다.'}
