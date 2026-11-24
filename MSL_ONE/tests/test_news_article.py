"""Article retrieval contracts; all fixtures are synthetic."""
import unittest
from unittest.mock import patch, Mock
from services import news_article as article


class ArticleTests(unittest.TestCase):
    def setUp(self):
        article._cache.clear()

    def test_private_address_and_non_http_are_rejected(self):
        for url in ('file:///etc/passwd', 'http://user:pass@example.org', 'http://example.org:22/test'):
            with self.assertRaises(ValueError):
                article.public_url(url)
        with patch.object(article.socket, 'getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 80))]):
            with self.assertRaises(ValueError):
                article.public_url('http://example.org/test')

    def test_metadata_summary_is_short_and_markup_free(self):
        text = ' '.join(f'word{i}' for i in range(60))
        summary, method = article.extract_summary(f'<meta property="og:description" content="{text}">')
        self.assertLessEqual(len(summary.split()), 25)
        self.assertIn('메타설명', method)
        self.assertNotIn('<', summary)

    def test_article_fallback_excludes_script_and_navigation(self):
        markup = '<nav>not article</nav><article><script>bad()</script><p>' + ('Synthetic article sentence. ' * 5) + '</p></article>'
        summary, method = article.extract_summary(markup)
        self.assertNotIn('bad()', summary)
        self.assertNotIn('not article', summary)
        self.assertIn('핵심 문장', method)

    def test_non_article_page_does_not_manufacture_a_summary(self):
        with self.assertRaises(ValueError):
            article.extract_summary('<html><nav>Home | Login</nav></html>')

    def test_success_caches_and_preserves_the_publisher_url(self):
        with patch.object(article, 'resolve_publisher', return_value='https://example.org/publisher'), patch.object(article, 'fetch_html', return_value=('https://example.org/final', '<meta name="description" content="Synthetic publisher description for the article content to test extraction.">', True)) as fetch:
            first = article.article_summary('https://news.google.com/rss/articles/TEST')
            second = article.article_summary('https://news.google.com/rss/articles/TEST')
        self.assertEqual(first['status'], 'ok')
        self.assertEqual(first['publisher_url'], 'https://example.org/final')
        self.assertTrue(second['cached'])
        self.assertEqual(fetch.call_count, 1)

    def test_failure_retains_link_and_does_not_claim_original_summary(self):
        with patch.object(article, 'resolve_publisher', side_effect=TimeoutError):
            result = article.article_summary('https://example.org/blocked')
        self.assertEqual(result['status'], 'unavailable')
        self.assertEqual(result['summary'], '')
        self.assertEqual(result['url'], 'https://example.org/blocked')

    def test_redirect_is_validated_before_fetching_the_next_hop(self):
        response = Mock(status_code=302, headers={'Location': 'http://127.0.0.1/secret'})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(article, 'public_url', side_effect=[None, ValueError('private')]), patch.object(article.requests, 'get', return_value=response) as get:
            with self.assertRaises(ValueError):
                article.fetch_html('https://example.org/start')
        self.assertEqual(get.call_count, 1)

    def test_publisher_frame_restriction_is_preserved(self):
        response = Mock(status_code=200, headers={'Content-Type':'text/html','X-Frame-Options':'SAMEORIGIN'})
        response.iter_content.return_value = [b'<article>synthetic</article>']
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        with patch.object(article, 'public_url'), patch.object(article.requests, 'get', return_value=response):
            _, _, allowed = article.fetch_html('https://example.org/article', include_policy=True)
        self.assertFalse(allowed)
