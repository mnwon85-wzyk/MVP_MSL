"""Bounded publisher-page retrieval and short extractive summaries; no LLM."""
from datetime import datetime, timezone
import ipaddress
import re
import socket
import time
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
import requests

_cache = {}


def public_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 80, 443):
        raise ValueError('Unsupported article URL')
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == 'https' else 80), type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Public publisher URL required')
    return url


def resolve_publisher(url):
    public_url(url)
    if urlsplit(url).hostname == 'news.google.com':
        if not re.fullmatch(r'/(?:rss/)?(?:articles|read)/[A-Za-z0-9_-]+', urlsplit(url).path):
            raise ValueError('Unsupported Google News URL')
        from googlenewsdecoder import gnewsdecoder
        result = gnewsdecoder(url, timeout=10)
        if not result.get('success'):
            raise ValueError('Publisher URL unavailable')
        url = result['decoded_url']
    if urlsplit(url).hostname in ('news.google.com', 'consent.google.com'):
        raise ValueError('Publisher URL unavailable')
    return public_url(url)


def fetch_html(url, include_policy=False):
    # Validate every redirect; never follow a publisher redirect into local services.
    for _ in range(5):
        public_url(url)
        with requests.get(url, timeout=(5, 12), allow_redirects=False, stream=True,
                          headers={'User-Agent': 'MSL-ONE-Portfolio/1.0 (public news preview)'}) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                url = urljoin(url, response.headers.get('Location', ''))
                continue
            response.raise_for_status()
            if 'html' not in response.headers.get('Content-Type', '').lower():
                raise ValueError('Publisher did not return HTML')
            chunks, size = [], 0
            for chunk in response.iter_content(32768):
                size += len(chunk)
                if size > 2_000_000:
                    raise ValueError('Article too large')
                chunks.append(chunk)
            frame_options = response.headers.get('X-Frame-Options', '').upper()
            ancestors = re.search(r'(?:^|;)\s*frame-ancestors\s+([^;]+)', response.headers.get('Content-Security-Policy', ''), re.I)
            blocked = 'DENY' in frame_options or 'SAMEORIGIN' in frame_options
            if ancestors and '*' not in ancestors.group(1).split():
                blocked = True
            page = (url, b''.join(chunks))
            return (*page, not blocked) if include_policy else page
    raise ValueError('Too many publisher redirects')


def extract_summary(markup):
    soup = BeautifulSoup(markup, 'html.parser')
    # Prefer a publisher-authored description; clearly identify it in the response.
    for selector in ('meta[property="og:description"]', 'meta[name="description"]', 'meta[name="twitter:description"]'):
        node = soup.select_one(selector)
        content = re.sub(r'\s+', ' ', BeautifulSoup(node.get('content', ''), 'html.parser').get_text(' ', strip=True)).strip() if node else ''
        if len(content) >= 45:
            return short_excerpt(content), '원문 메타설명 발췌'
    for node in soup.select('script,style,nav,footer,aside,form'):
        node.decompose()
    article = soup.select_one('article, [itemprop="articleBody"], #article-view-content-div, #news_body_area, #articleBody, #newsct_article, .article-body, .news-view-content')
    if article:
        for line in article.get_text('\n', strip=True).splitlines():
            if len(line) >= 65 and not re.search(r'무단.?전재|재배포.?금지|로그인|구독하기', line):
                return short_excerpt(line), '원문 핵심 문장 발췌'
    raise ValueError('Readable publisher summary unavailable')


def short_excerpt(text):
    # Keep quoted publisher material short; never expose the full article body.
    words = text.split()
    excerpt = ' '.join(words[:25])
    shortened = len(words) > 25 or len(excerpt) > 260
    return excerpt[:260].rstrip() + ('…' if shortened else '')


def article_summary(url):
    cached = _cache.get(url)
    if cached and time.monotonic() - cached[0] < (1800 if cached[1]['status'] == 'ok' else 60):
        return {**cached[1], 'cached': True}
    result = {'status': 'unavailable', 'url': url, 'publisher_url': None, 'summary': '',
              'retrieved_at': datetime.now(timezone.utc).isoformat(), 'cached': False,
              'embedding_allowed': None,
              'method': '원문에서 짧은 핵심 설명 추출 · LLM 미사용'}
    try:
        publisher_url = resolve_publisher(url)
        result['publisher_url'] = publisher_url
        final_url, markup, embedding_allowed = fetch_html(publisher_url, include_policy=True)
        result.update(publisher_url=final_url, embedding_allowed=embedding_allowed)
        summary, method = extract_summary(markup)
        result.update(status='ok', publisher_url=final_url, summary=summary, method=method)
    except Exception as exc:
        result['error'] = type(exc).__name__
        result['message'] = '원문 요약을 불러오지 못했습니다. 원문 기사 열기에서 확인하세요.'
    _cache[url] = (time.monotonic(), result)
    if len(_cache) > 100:
        _cache.pop(next(iter(_cache)))
    return result
