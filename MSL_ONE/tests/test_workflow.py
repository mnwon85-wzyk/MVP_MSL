"""Offline contract tests. Fixtures are synthetic test records, never application demo evidence."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

_temporary = tempfile.TemporaryDirectory()
os.environ['MSL_WORKFLOW_DB'] = str(Path(_temporary.name) / 'workflow.sqlite3')
import api
import workflow_api
import workflow_store
from workflow_sources import source_key

CONTEXT = {'hcp':'Synthetic test HCP','disease':'Test disease','scientific_question':'Synthetic test question?'}
EVIDENCE = {'source':'PubMed','id':'TEST_ONLY','title':'Synthetic contract test record','url':'https://example.org/test-only','abstract':'Test fixture, not scientific evidence.'}
RESULT = {'evidence':[EVIDENCE], 'treatment':[], 'source_status':{'PubMed':{'status':'ok'},'FDA':{'status':'unavailable'}}, 'source_totals':{'PubMed':1}, 'queries':{}, 'limitations':['Synthetic test fixture']}

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)

    def create(self, **extra):
        with patch.object(workflow_api, 'retrieve', return_value=RESULT):
            response=self.client.post('/workflow/prepares',json={'context':CONTEXT, **extra})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def test_persistence_and_history(self):
        session=self.create()
        selected=self.client.patch('/workflow/prepares/'+session['id'],json={'revision':session['revision'],'selected_keys':[source_key(EVIDENCE)]})
        self.assertEqual(selected.status_code,200)
        self.assertEqual(self.client.get(f"/workflow/prepares/{session['id']}?revision={session['revision']}").json()['selected_keys'],[])
        stale=self.client.patch('/workflow/prepares/'+session['id'],json={'revision':session['revision'],'selected_keys':[]})
        self.assertEqual(stale.status_code,409)
        # A fresh interpreter must reconstruct evidence/selection from SQLite.
        output=subprocess.check_output([os.sys.executable,'-c', f"import workflow_store; s=workflow_store.get_session('{session['id']}'); assert len(s['selected_keys']) == 1; print('restored')"],env=os.environ.copy())
        self.assertIn(b'restored',output)
        newer=self.create(parent_id=session['id'])
        self.assertEqual(newer['parent_id'],session['id'])
        self.assertEqual(newer['comparison']['newly_retrieved'],[])
        self.assertEqual(self.client.get('/workflow/prepares/'+session['id']).json()['selected_keys'],[source_key(EVIDENCE)])

    def test_complete_loop_brief_package_ai_failure(self):
        session=self.create()
        session=self.client.patch('/workflow/prepares/'+session['id'],json={'revision':session['revision'],'selected_keys':[source_key(EVIDENCE)]}).json()
        with patch.object(api, '_call_llm', side_effect=RuntimeError('Synthetic unavailable')):
            failed=self.client.post(f"/workflow/prepares/{session['id']}/analysis",json={'language':'en','revision':session['revision']})
        self.assertEqual(failed.status_code,500)
        self.assertEqual(self.client.get('/workflow/prepares/'+session['id']).json()['evidence'],[EVIDENCE])
        for lang in ('en','kr'):
            response=self.client.post(f"/workflow/prepares/{session['id']}/brief",json={'language':lang,'revision':session['revision']})
            self.assertEqual(response.status_code,200,response.text)
            session=response.json()
            self.assertIn(EVIDENCE['url'],session['briefs'][lang]['answer'])
        r=self.client.post('/workflow/interactions',json={'prepare_id':session['id'],'observation':'Synthetic HCP observation','scientific_question':'Synthetic unresolved question?','date':'2026-10-06'}).json()
        with patch.object(api, '_call_llm', side_effect=RuntimeError('Synthetic unavailable')):
            analyzed=self.client.post(f"/workflow/interactions/{r['id']}/analyze",json={'use_ai':True}).json()
        self.assertEqual(analyzed['ai_status'],'unavailable')
        self.assertTrue(analyzed['analysis']['review_required'])
        q=self.client.post('/workflow/questions',json={'interaction_id':r['id'],'scientific_question':'Synthetic unresolved question?'}).json()
        self.assertEqual(q['prepare_id'],session['id'])
        self.assertIn(q['id'],[q['id'] for q in self.client.get('/workflow/state').json()['questions']])
        package=self.client.get(f"/workflow/prepares/{session['id']}/package").json()
        self.assertIn(EVIDENCE['url'],package['source_urls'])

    def test_cached_signals(self):
        session=self.create()
        # Router holds legacy globals: replace the existing endpoint for this test only.
        with patch.dict(api.__dict__, {'listen':lambda request: {'items':[], 'count':0}}):
            s=self.client.post(f"/workflow/prepares/{session['id']}/signals",json={'revision':session['revision'],'language':'en'}).json()
        self.assertEqual(s['signals']['status'],'loaded')
        with patch.dict(api.__dict__, {'listen':lambda request: self.fail('Repeated external signal retrieval')}):
            cached=self.client.post(f"/workflow/prepares/{s['id']}/signals",json={'revision':s['revision'],'language':'en'}).json()
        self.assertEqual(cached['revision'],s['revision'])

    def test_notes_tasks_and_invalid_context(self):
        self.assertEqual(self.client.post('/workflow/prepares',json={'context':{'disease':' '}}).status_code,400)
        self.client.put('/workflow/note',json={'note':'Persistent synthetic note'})
        task=self.client.post('/workflow/tasks',json={'title':'Synthetic task'}).json()
        self.client.put('/workflow/tasks/'+task['id'],json={'title':task['title'],'complete':True})
        state=self.client.get('/workflow/state').json()
        self.assertEqual(state['note'],'Persistent synthetic note')
        self.assertTrue(next(t for t in state['tasks'] if t['id']==task['id'])['complete'])

    def test_regulatory_verification_is_not_trial_approval(self):
        from workflow_sources import ema_context
        raw={'source':'EMA','id':'TEST','title':'Synthetic','status':'Withdrawn','therapeutic_indication':'Test disease'}
        with patch('workflow_sources.search_ema_medicines',return_value=[raw]):
            result=ema_context(CONTEXT)
        self.assertEqual(len(result['evidence']),1)
        self.assertEqual(result['treatment'],[])

    def test_exports_remain_available(self):
        request={'report_type':'internal','language':'English','analysis_result':{'answer':'Synthetic export smoke test. No scientific conclusions.'},'evidence':[]}
        with tempfile.TemporaryDirectory() as export_dir:
            import services.dashboard as dashboard
            with patch.object(dashboard, 'EXPORT_DIR', Path(export_dir)):
                for fmt, signature in [('pdf',b'%PDF'),('pptx',b'PK')]:
                    response=self.client.post('/reports/export/'+fmt,json=request)
                    self.assertEqual(response.status_code,200,response.text[:200])
                    self.assertTrue(response.content.startswith(signature))

    def test_ai_gap_citation_validation_and_revision(self):
        session=self.create()
        session=self.client.patch('/workflow/prepares/'+session['id'],json={'revision':session['revision'],'selected_keys':[source_key(EVIDENCE)]}).json()
        import json
        invalid=[{'kind':'Test','question':'Test?','basis':'Test fixture','source_keys':['fabricated:key']}]
        with patch.object(api, '_call_llm', return_value=json.dumps(invalid)):
            response=self.client.post(f"/workflow/prepares/{session['id']}/gaps",json={'revision':session['revision']})
        self.assertEqual(response.status_code,502)
        self.assertEqual(self.client.get('/workflow/prepares/'+session['id']).json()['revision'],session['revision'])
        invalid[0]['source_keys']=[source_key(EVIDENCE)]
        with patch.object(api, '_call_llm', return_value=json.dumps(invalid)):
            response=self.client.post(f"/workflow/prepares/{session['id']}/gaps",json={'revision':session['revision']})
        self.assertEqual(response.status_code,200,response.text)
        self.assertTrue(response.json()['gaps'][0]['review_required'])

    def test_morning_intelligence_uses_source_dates(self):
        workflow_store.setting('context',CONTEXT)
        workflow_store.setting('intelligence',{})
        old={**EVIDENCE,'date':'2019 Jan 01'}
        with patch.object(workflow_api, 'retrieve', return_value={**RESULT,'evidence':[old]}):
            response=self.client.post('/workflow/intelligence/refresh',json={})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['changes'],[])

    def test_fda_url_handles_anda_before_nda(self):
        from services.fda import fda_drugs_page
        self.assertTrue(fda_drugs_page('ANDA205242').endswith('ApplNo=205242'))

    def test_prior_question_snapshot_does_not_change_with_status(self):
        base=self.create()
        interaction=self.client.post('/workflow/interactions',json={'prepare_id':base['id'],'observation':'Synthetic test observation'}).json()
        question=self.client.post('/workflow/questions',json={'interaction_id':interaction['id'],'scientific_question':'Synthetic question?'}).json()
        context={**CONTEXT,'related_question_id':question['id'],'interaction_id':interaction['id']}
        with patch.object(workflow_api, 'retrieve', return_value=RESULT):
            session=self.client.post('/workflow/prepares',json={'context':context}).json()
        self.client.patch('/workflow/questions/'+question['id'],json={'status':'RESOLVED'})
        snapshot=self.client.get(f"/workflow/prepares/{session['id']}/package?revision={session['revision']}").json()
        saved_question=next(q for q in snapshot['follow_up_questions'] if q['id']==question['id'])
        self.assertEqual(saved_question['status'],'OPEN')
        self.assertEqual(snapshot['revision'],session['revision'])


    def test_multicategory_basket_analysis_snapshot_and_exports(self):
        import json
        import io
        from pptx import Presentation
        session = self.create()
        treatment = {**EVIDENCE, 'source':'FDA', 'id':'TEST_REGULATORY'}
        signal = {**EVIDENCE, 'source':'Public forum', 'id':'TEST_SIGNAL'}
        unselected = {**EVIDENCE, 'id':'UNSELECTED_ONLY', 'title':'Must not enter basket analysis'}
        session = workflow_store.update_session(session['id'], {'treatment':[treatment], 'signals':{'status':'loaded','items':[signal]}, 'evidence':[EVIDENCE,unselected]}, session['revision'])
        choice = {'treatment':[source_key(treatment)], 'signals':[source_key(signal)], 'gaps':['question-review']}
        response = self.client.patch('/workflow/prepares/'+session['id'], json={'revision':session['revision'], 'selected_keys':[source_key(EVIDENCE)], 'selected_context':choice})
        self.assertEqual(response.status_code,200,response.text)
        session=response.json()
        self.assertEqual(len(session['gaps']),1)
        invalid=self.client.patch('/workflow/prepares/'+session['id'], json={'revision':session['revision'], 'selected_keys':[], 'selected_context':{'signals':['invented']}})
        self.assertEqual(invalid.status_code,400)
        with patch.object(api, '_call_llm', return_value='Synthetic basket analysis only.') as llm:
            response=self.client.post(f"/workflow/prepares/{session['id']}/analysis",json={'revision':session['revision'],'language':'en'})
        self.assertEqual(response.status_code,200,response.text)
        inputs=json.loads(llm.call_args.args[2])
        self.assertEqual([i['category'] for i in inputs['selected_basket']],['evidence','treatment','signals','gaps'])
        self.assertNotIn('UNSELECTED_ONLY',llm.call_args.args[2])
        result=response.json()['analyses']['en']
        newer=self.client.patch('/workflow/prepares/'+session['id'],json={'revision':response.json()['revision'],'selected_keys':[],'selected_context':{}}).json()
        self.assertEqual(len(newer['analyses']['en']['basket_items']),4)
        report={'report_type':'internal','language':'English','analysis_result':result,'metadata':{'workflow_output':True,'basket_analysis':True,'language':'en'},'evidence':[dict(i['record'],title=i['record'].get('title') or i['record'].get('question'),source=i['category']) for i in result['basket_items']]}
        import services.dashboard as dashboard
        with tempfile.TemporaryDirectory() as export_dir, patch.object(dashboard,'EXPORT_DIR',Path(export_dir)):
            pdf=self.client.post('/reports/export/pdf',json=report)
            pptx=self.client.post('/reports/export/pptx',json=report)
        self.assertEqual(pdf.status_code,200)
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        self.assertEqual(pptx.status_code,200)
        slides=Presentation(io.BytesIO(pptx.content))
        texts=' '.join(shape.text for slide in slides.slides for shape in slide.shapes if shape.has_text_frame)
        self.assertIn(result['answer'],texts)
        self.assertIn('TEST_REGULATORY',texts)
        self.assertIn('TEST_SIGNAL',texts)
        self.assertNotIn('UNSELECTED_ONLY',texts)

    def test_context_only_basket_can_be_analyzed(self):
        session=self.create()
        session=self.client.patch('/workflow/prepares/'+session['id'],json={'revision':session['revision'],'selected_keys':[],'selected_context':{'gaps':['question-review']}}).json()
        with patch.object(api,'_call_llm',return_value='Synthetic gap review, not clinical evidence.'):
            response=self.client.post(f"/workflow/prepares/{session['id']}/analysis",json={'revision':session['revision']})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()['analyses']['en']['basket_items'][0]['category'],'gaps')



    def test_gemini_key_is_local_and_never_echoed(self):
        secret = 'synthetic-test-key-not-a-real-secret'
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('GEMINI_API_KEY',None)
            status=self.client.get('/workflow/gemini').json()
            self.assertFalse(status['configured'])
            denied=self.client.put('/workflow/gemini',json={'api_key':secret},headers={'origin':'https://untrusted.example'})
            self.assertEqual(denied.status_code,403)
            saved=self.client.put('/workflow/gemini',json={'api_key':secret},headers={'origin':'http://127.0.0.1:5173'})
            self.assertEqual(saved.status_code,200)
            self.assertTrue(saved.json()['configured'])
            self.assertNotIn(secret,saved.text)
            self.assertNotIn(secret,self.client.get('/workflow/state').text)
            with patch.object(api,'_call_llm',return_value='OK'):
                self.assertTrue(self.client.post('/workflow/gemini/test').json()['connected'])
            with patch.object(api,'_call_llm',side_effect=RuntimeError('Provider leaked '+secret)):
                failed=self.client.post('/workflow/gemini/test')
            self.assertEqual(failed.status_code,503)
            self.assertNotIn(secret,failed.text)
            self.assertEqual(self.client.put('/workflow/gemini',json={'api_key':'short'}).status_code,400)

    def test_curated_gsk_sample_has_both_drugs_and_real_source_ids(self):
        import workflow_sample
        ruby={**EVIDENCE,'id':'36972026','title':'Synthetic RUBY test response'}
        nrg={**EVIDENCE,'id':'36972022','title':'Synthetic NRG test response'}
        with patch.object(workflow_sample,'literature',return_value=[ruby,nrg]), patch.object(workflow_sample,'trial',return_value=[]):
            response=self.client.post('/workflow/samples/gsk-oncology')
        self.assertEqual(response.status_code,200,response.text)
        sample=response.json()
        self.assertTrue(sample['sample'])
        self.assertIn('dostarlimab',sample['context']['drugs'])
        self.assertIn('pembrolizumab',sample['context']['drugs'])
        self.assertEqual(len(sample['selected_keys']),2)
        self.assertEqual(len(sample['selected_context']['treatment']),2)
        self.assertEqual(len(sample['selected_context']['gaps']),1)
        self.assertEqual(sample['analyses'],{})
        self.assertEqual(sample['briefs']['kr']['method'],'Source compilation')
        self.assertIn('Jemperli',self.client.get(f"/workflow/prepares/{sample['id']}/package").text)

if __name__ == '__main__': unittest.main()
