import json
import tempfile
import unittest
from pathlib import Path
from datetime import date
from skra.answer import answer, Ledger
from skra.boundaries import load_cases, prepare, contract_response
from skra.store import Store

class BoundaryContractTest(unittest.TestCase):
    def test_authored_response_contracts_are_rendered_without_executing_tools(self):
        for case in load_cases():
            with self.subTest(case=case['id']), tempfile.TemporaryDirectory() as tmp:
                store=Store(Path(tmp)/'docs.db'); ledger=Ledger(Path(tmp)/'budget.db')
                try:
                    evidence,search=prepare(store,Path(tmp)/'docs',case)
                    def send(payload,key,timeout):
                        self.assertNotIn('tools',payload)
                        self.assertEqual(payload['messages'][0]['role'],'system')
                        self.assertEqual(payload['messages'][1]['role'],'user')
                        return {'usage':{'prompt_tokens':100,'completion_tokens':100},
                            'choices':[{'finish_reason':'stop','message':{'content':json.dumps(contract_response(case,evidence))}}]}
                    config={'verified':True,'verified_at':date.today().isoformat(),'model':'fixture',
                        'input_bound_strategy':'context-window','context_token_upper_bound':1048576,
                        'input_rmb_per_million':1,'output_rmb_per_million':2}
                    result=answer(store,case['question'],ledger,config,'test-key',send=send,search=search)
                    self.assertEqual(result['status'],case['expected_status'])
                    self.assertEqual(len(result['citations']),0 if case['expected_status']=='insufficient' else len(evidence))
                    self.assertEqual(store.run(result['retrieval_run_id'])['mode'],'controlled-evidence-not-retrieval')
                finally:store.close();ledger.close()
