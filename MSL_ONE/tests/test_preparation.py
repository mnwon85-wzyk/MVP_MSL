import base64
import unittest
from unittest.mock import patch
from starlette.requests import Request
from cvrm_api import PreparationUpload, preparation_file, PreparationRequest, preparation

class PreparationTests(unittest.TestCase):
    def test_extract_text(self):
        result=preparation_file(PreparationUpload(name='note.txt',base64=base64.b64encode('논문 검토'.encode()).decode()))
        self.assertEqual(result['text'],'논문 검토')
    def test_reject_non_document(self):
        self.assertEqual(preparation_file(PreparationUpload(name='run.exe',base64='YWJj'))['status'],'unavailable')
    @patch('services.preparation.answer')
    @patch('cvrm_api.search_news',return_value={'status':'ok','items':[]})
    @patch('cvrm_api.source_result',return_value={'status':'ok','items':[{'id':'1','title':'paper','abstract':'abstract'}]})
    def test_search_without_llm(self,papers,news,answer):
        result=preparation(PreparationRequest(question='question',query='finerenone',news_query='케렌디아'),Request({'type':'http','headers':[]}))
        self.assertEqual(result['papers']['items'][0]['id'],'1')
        answer.assert_not_called()
