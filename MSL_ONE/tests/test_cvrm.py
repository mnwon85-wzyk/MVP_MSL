"""Offline CVRM contracts. Synthetic fixtures are never product evidence."""
import unittest
from unittest.mock import patch, Mock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import cvrm_api as cv
from services.pubmed import _parse_articles

class CvrmTests(unittest.TestCase):
    def setUp(self):
        app=FastAPI()
        app.include_router(cv.router)
        self.client=TestClient(app)
        cv._news_cache.clear()

    def test_search_records_status_and_separate_queries(self):
        fixture={'items':[{'id':'TEST_ONLY','title':'Synthetic contract fixture'}],'total':31}
        with patch.object(cv,'search_pubmed_paginated',return_value=fixture) as papers, patch.object(cv,'search_trials_paginated',return_value={'items':[],'total':0}) as trials:
            r=self.client.post('/cvrm/search',json={'query':'test[Author]','trial_query':'test condition','page':2}).json()
        self.assertEqual(r['papers']['total'],31)
        self.assertEqual(r['trials']['items'],[])
        papers.assert_called_once_with('test[Author]',page=2,page_size=12)
        trials.assert_called_once_with('test condition',page=2,page_size=12)

    def test_source_failure_does_not_substitute_saved_records(self):
        with patch.object(cv,'search_pubmed_paginated',side_effect=TimeoutError),patch.object(cv,'search_trials_paginated',return_value={'items':[],'total':0}):
            r=self.client.post('/cvrm/search',json={'query':'test'}).json()
        self.assertEqual(r['papers']['status'],'unavailable')
        self.assertIsNone(r['papers']['total'])
        self.assertEqual(r['papers']['items'],[])
        self.assertEqual(r['trials']['status'],'ok')

    def test_invalid_query_and_page_are_rejected(self):
        for data in ({'query':''},{'query':'x','page':0},{'query':'x','page':11},{'query':'x'*701}):
            self.assertEqual(self.client.post('/cvrm/search',json=data).status_code,422)

    def test_rss_strips_markup_and_preserves_access_level(self):
        xml=b'<rss><channel><item><guid>TEST_ONLY</guid><title>Test &amp; fixture</title><link>https://example.org/test</link><source>Test publisher</source><description>&lt;b&gt;Synthetic excerpt&lt;/b&gt;</description></item><item><link>javascript:alert(1)</link></item></channel></rss>'
        response=Mock(content=xml)
        with patch.object(cv.requests,'get',return_value=response) as get:
            a=cv.search_news('test');b=cv.search_news('test')
        self.assertEqual(a['items'][0]['summary'],'Synthetic excerpt')
        self.assertEqual(len(a['items']),1)
        self.assertIn('original article not reviewed',a['items'][0]['access'])
        self.assertTrue(b['cached']);self.assertEqual(get.call_count,1)

    def test_news_failure_is_visible(self):
        with patch.object(cv.requests,'get',side_effect=TimeoutError):r=cv.search_news('test')
        self.assertEqual(r['status'],'unavailable');self.assertEqual(r['items'],[])

    def test_review_retains_source_states_and_does_not_invent_conclusion(self):
        base={'papers':{'status':'ok','items':[],'total':0},'trials':{'status':'unavailable','items':[],'total':None},'retrieved_at':'test'}
        with patch.object(cv,'search_public',return_value=base),patch.object(cv,'search_news',return_value={'status':'ok','items':[]}):
            r=self.client.post('/cvrm/review',json={'query':'test'}).json()
        self.assertEqual(r['trials']['status'],'unavailable');self.assertNotIn('answer',r)
        self.assertIn('human review',r['analysis']['method'])

    def test_author_affiliation_metadata_is_available_for_disambiguation(self):
        xml='<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>000TEST</PMID><Article><ArticleTitle>Synthetic fixture</ArticleTitle><AuthorList><Author><LastName>Test</LastName><ForeName>Author</ForeName><AffiliationInfo><Affiliation>Synthetic university</Affiliation></AffiliationInfo></Author></AuthorList></Article></MedlineCitation></PubmedArticle></PubmedArticleSet>'
        r=_parse_articles(xml)[0]
        self.assertEqual(r['authors'],['Test Author']);self.assertEqual(r['affiliations'],['Synthetic university'])

    def test_standalone_served_with_success(self):
        r=self.client.get('/cvrm')
        self.assertEqual(r.status_code,200);self.assertIn('CVRM workspace',r.text)
        self.assertIn('cv-sidebar',r.text)

    def test_article_route_preserves_the_fetch_status(self):
        with patch.object(cv, 'article_summary', return_value={'status':'unavailable','summary':'','url':'https://example.org/test'}) as fetch:
            result = self.client.post('/cvrm/news/article', json={'url':'https://example.org/test'}).json()
        self.assertEqual(result['status'], 'unavailable')
        fetch.assert_called_once_with('https://example.org/test')
