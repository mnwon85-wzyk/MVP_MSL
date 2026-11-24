"""No real LLM calls; verify session isolation and input/source boundaries."""
import json
import unittest
from unittest.mock import patch, Mock
from fastapi import FastAPI
from fastapi.testclient import TestClient
import cvrm_api as cv
from services import question_analysis as qa


class QuestionAnalysisTests(unittest.TestCase):
    def setUp(self):
        qa._sessions.clear()
        app = FastAPI()
        app.include_router(cv.router)
        self.client = TestClient(app)
        self.other = TestClient(app)

    def test_no_connection_never_calls_the_model(self):
        with patch.object(qa, 'generate_questions') as generate:
            result = self.client.post('/cvrm/question/analyze', json={'question':'Synthetic question'}).json()
        self.assertEqual(result['status'], 'needs_connection')
        generate.assert_not_called()

    def test_key_is_ephemeral_and_scoped_to_one_browser(self):
        key = 'sk-SYNTHETIC-NOT-A-REAL-KEY'
        result = self.client.post('/cvrm/llm/connect', json={'api_key':key,'model':'test-model'})
        self.assertNotIn(key, result.text)
        self.assertIn('HttpOnly', result.headers['set-cookie'])
        self.assertTrue(self.client.post('/cvrm/llm/status').json()['configured'])
        self.assertFalse(self.other.post('/cvrm/llm/status').json()['configured'])
        self.client.post('/cvrm/llm/disconnect')
        self.assertFalse(self.client.post('/cvrm/llm/status').json()['configured'])

    def test_short_key_is_rejected_without_echoing_the_value(self):
        result = self.client.post('/cvrm/llm/connect', json={'api_key':'SECRET_SHORT','model':'test-model'})
        self.assertNotIn('SECRET_SHORT', result.text)
        self.assertFalse(result.json()['configured'])

    def test_transcript_requires_explicit_inclusion(self):
        self.client.post('/cvrm/llm/connect', json={'api_key':'sk-SYNTHETIC-NOT-A-REAL-KEY','model':'test-model'})
        with patch.object(qa, 'search_pubmed_paginated', return_value={'items':[]}), patch.object(qa, 'generate_questions', return_value={'summary':'test','questions':[]}) as generate:
            result = self.client.post('/cvrm/question/analyze', json={'question':'Typed question','transcript':'EXCLUDED TEXT','include_transcript':False}).json()
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(generate.call_args.args[2], 'Typed question')

    def test_expired_key_requires_reconnection(self):
        token = qa.connect('synthetic', 'test')
        qa._sessions[token]['created'] -= 3601
        self.assertFalse(qa.settings(token)['configured'])
        self.assertNotIn(token, qa._sessions)

    def test_provider_failure_never_returns_credentials_or_submitted_text(self):
        token = qa.connect('SYNTHETIC-SECRET', 'test')
        with patch.object(qa, 'search_pubmed_paginated', return_value={'items':[]}), patch.object(qa, 'generate_questions', side_effect=Exception('SYNTHETIC-SECRET submitted text')):
            result = qa.analyze(token, 'submitted text', '', False, 'finerenone')
        self.assertEqual(result['status'], 'unavailable')
        self.assertNotIn('SYNTHETIC-SECRET', json.dumps(result))
        self.assertNotIn('submitted text', json.dumps(result))

    def test_unknown_model_citation_is_rejected(self):
        output = {'summary':'test','keywords':['test'],'questions':[{'question':'test?','rationale':'test','source_ids':['FAKE']} for _ in range(3)],'search_terms':['test']}
        response = Mock()
        response.json.return_value = {'output':[{'content':[{'type':'output_text','text':json.dumps(output)}]}]}
        with patch.object(qa.requests, 'post', return_value=response):
            with self.assertRaises(ValueError):
                qa.generate_questions('synthetic','test','test',[])

    def test_provider_request_uses_server_key_and_disables_response_storage(self):
        output = {'summary':'test','keywords':['test'],'questions':[{'question':'test?','rationale':'test','source_ids':['123']} for _ in range(3)],'search_terms':['test']}
        response = Mock()
        response.json.return_value = {'output':[{'content':[{'type':'output_text','text':json.dumps(output)}]}]}
        with patch.object(qa.requests, 'post', return_value=response) as post:
            result = qa.generate_questions('synthetic','test','test',[{'id':'123','title':'Synthetic source'}])
        self.assertEqual(len(result['questions']), 3)
        self.assertFalse(post.call_args.kwargs['json']['store'])
        self.assertEqual(post.call_args.kwargs['json']['text']['format']['type'], 'json_schema')
