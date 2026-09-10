"""Captured live failures, replayed at the public answer boundary without API calls."""
import copy
import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path

from skra.answer import Ledger, answer
from skra.store import Store
from skra.cli import main

ROOT = Path(__file__).resolve().parents[1]


class QuestionCoverageTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db_path = Path(temp.name) / 'docs.db'
        self.store = Store(self.db_path)
        self.ledger = Ledger(Path(temp.name) / 'budget.db')
        self.addCleanup(self.store.close)
        self.addCleanup(self.ledger.close)
        report = json.loads((ROOT / 'docs/evidence/issue05-live-20260909.json').read_text(encoding='utf-8'))
        self.partial = next(c for c in report['cases'] if c['id'] == 'partial')
        self.conditions = json.loads((ROOT / 'docs/evidence/issue05-conditions-failure.json').read_text(encoding='utf-8'))

    def run_body(self, question, evidence, body):
        def search(query, limit):
            result = {'query': query, 'candidates': evidence}
            with self.store.db:
                row = self.store.db.execute(
                    "INSERT INTO runs(created,query,result,elapsed_ms) VALUES ('offline',?,?,0)",
                    (query, json.dumps(result)))
            return {**result, 'run_id': row.lastrowid}

        def send(payload, key, timeout):
            self.request = json.loads(payload['messages'][1]['content'])
            return {'usage': {'prompt_tokens': 100, 'completion_tokens': 100},
                    'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(body)}}]}

        config = {'verified': True, 'verified_at': date.today().isoformat(), 'model': 'offline-fixture',
                  'input_bound_strategy': 'context-window', 'context_token_upper_bound': 1048576,
                  'input_rmb_per_million': 1, 'output_rmb_per_million': 2}
        return answer(self.store, question, self.ledger, config, 'fixture-key', send=send, search=search)

    def partial_body(self):
        return {k: copy.deepcopy(self.partial['result'][k])
                for k in ('status', 'claims', 'citations', 'missing')}

    def test_missing_measurement_can_cite_scope_without_claiming_an_answer(self):
        failure = json.loads((ROOT / 'docs/evidence/issue05-v31-measurement-failure.json').read_text(encoding='utf-8'))
        body = json.loads(failure['record']['model_output'])
        result = self.run_body(failure['query'], failure['retrieval']['candidates'], body)
        self.assertEqual(result['status'], 'insufficient')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['citation_scope'], 'missing_context')
        self.assertEqual(result['citations'][0]['quote'], body['citations'][0]['quote'])
        self.assertEqual(result['coverage'], body['coverage'])
        for field, value in [('id', 'fake'), ('quote', 'fabricated')]:
            bad = copy.deepcopy(body)
            bad['citations'][0][field] = value
            with self.assertRaisesRegex(ValueError, '引用'):
                self.run_body(failure['query'], failure['retrieval']['candidates'], bad)

    def test_identical_nested_live_citation_is_normalized_without_changing_coverage(self):
        failure = json.loads((ROOT / 'docs/evidence/issue05-v3-principle-failure.json').read_text(encoding='utf-8'))
        body = json.loads(failure['record']['model_output'])
        original = copy.deepcopy(body)
        result = self.run_body(failure['query'], failure['retrieval']['candidates'], body)
        self.assertEqual(result['claims'][0]['citations'], [body['citations'][0]['id']])
        self.assertEqual(result['coverage'], body['coverage'])
        self.assertEqual(result['status'], 'partial')  # Semantic error remains visible.
        self.assertIn('操作细节', result['missing'])
        self.assertEqual(body, original)
        self.assertIn('identical_inline_citation_to_id', result['normalizations'])

    def test_conflicting_or_incomplete_nested_citations_are_not_silently_discarded(self):
        failure = json.loads((ROOT / 'docs/evidence/issue05-v3-principle-failure.json').read_text(encoding='utf-8'))
        for change in ({'quote': 'fabricated'}, {'translation': '不同释义'}, {'id': 'fake'},
                       {'extra': 'unexpected'}, {'quote': None}):
            with self.subTest(change=change):
                body = json.loads(failure['record']['model_output'])
                body['claims'][0]['citations'][0].update(change)
                with self.assertRaisesRegex(ValueError, '引用'):
                    self.run_body(failure['query'], failure['retrieval']['candidates'], body)
        body = json.loads(failure['record']['model_output'])
        body['citations'] = []
        with self.assertRaisesRegex(ValueError, '引用'):
            self.run_body(failure['query'], failure['retrieval']['candidates'], body)

    def test_two_distinct_quotes_from_one_chunk_are_kept_not_rejected(self):
        # Live acceptance run Q01 (call_id=34) halted here: the model quoted two
        # different sentences from the SAME evidence chunk, which the validator
        # rejected as a duplicate id. Both quotes are real substrings, so both
        # must be preserved; distinct quotes must not be silently discarded.
        failure = json.loads((ROOT / 'docs/evidence/issue05-acceptance-q01-duplicate-citation-failure.json').read_text(encoding='utf-8'))
        body = json.loads(failure['model_output'])
        ids = [c['id'] for c in body['citations']]
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(set(ids)), 1, '前置条件：本题模型对同一片段给出两条不同 quote。')
        quotes = {c['quote'] for c in body['citations']}
        self.assertEqual(len(quotes), 2)
        result = self.run_body(failure['query'], failure['retrieval']['candidates'], body)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(len(result['citations']), 2)
        self.assertEqual({c['quote'] for c in result['citations']}, quotes)
        self.assertEqual(result['claims'][0]['citations'], [ids[0]])

    def test_duplicate_id_with_conflicting_quote_is_still_rejected(self):
        # Allowing repeated ids must not weaken verification: a repeated id whose
        # quote is not a verbatim substring is still rejected.
        failure = json.loads((ROOT / 'docs/evidence/issue05-acceptance-q01-duplicate-citation-failure.json').read_text(encoding='utf-8'))
        body = json.loads(failure['model_output'])
        body['citations'][1]['quote'] = 'invented quote that is not in the chunk'
        with self.assertRaisesRegex(ValueError, '引用'):
            self.run_body(failure['query'], failure['retrieval']['candidates'], body)

    def test_original_partial_omission_is_no_longer_accepted(self):
        with self.assertRaisesRegex(ValueError, '问题覆盖'):
            self.run_body(self.partial['question'], self.partial['result']['citations'], self.partial_body())
        run_id = self.store.db.execute('SELECT MAX(id) FROM runs').fetchone()[0]
        with contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(main(['--db', str(self.db_path), 'replay', str(run_id)]), 2)
        self.assertIn('问题覆盖', errors.getvalue())

    def test_partial_requires_each_question_and_derives_status(self):
        body = self.partial_body()
        body['coverage'] = [{'question_id': 'q1', 'claims': [0], 'missing': ''}]
        with self.assertRaisesRegex(ValueError, '问题覆盖'):
            self.run_body(self.partial['question'], self.partial['result']['citations'], body)
        body['coverage'].append({'question_id': 'q2', 'claims': [], 'missing': '资料未给出具体数量。'})
        result = self.run_body(self.partial['question'], self.partial['result']['citations'], body)
        self.assertEqual(result['status'], 'partial')
        self.assertIn('具体数量', result['missing'])
        self.assertEqual(result['claims'], body['claims'])
        self.assertEqual([q['text'] for q in self.request['questions']], ['应如何限制工具？', '具体最多几项？'])
        self.assertNotIn('expected_status', self.request)

    def test_conditions_coverage_not_model_status_controls_result(self):
        body = json.loads(self.conditions['record']['model_output'])
        body['coverage'] = [{'question_id': 'q1', 'claims': [0], 'missing': ''}]
        result = self.run_body(self.conditions['retrieval']['query'], self.conditions['retrieval']['candidates'], body)
        self.assertEqual(result['status'], 'grounded')
        self.assertEqual(result['missing'], '')
        self.assertEqual(result['claims'], body['claims'])
        self.assertEqual(len(result['citations']), 2)

    def test_original_conditions_is_not_blindly_promoted(self):
        with self.assertRaisesRegex(ValueError, '问题覆盖'):
            self.run_body(self.conditions['retrieval']['query'], self.conditions['retrieval']['candidates'],
                          json.loads(self.conditions['record']['model_output']))

    def test_supported_number_and_real_partial_are_not_forced_to_grounded(self):
        body = self.partial_body()
        evidence = copy.deepcopy(self.partial['result']['citations'])
        evidence[0]['text'] += ' Grant at most three tools.'
        body['citations'][0]['quote'] = evidence[0]['text']
        body['claims'].append({'text': '最多三个工具。', 'citations': [evidence[0]['id']]})
        body['coverage'] = [{'question_id': 'q1', 'claims': [0], 'missing': ''},
                            {'question_id': 'q2', 'claims': [1], 'missing': ''}]
        result = self.run_body(self.partial['question'], evidence, body)
        self.assertEqual(result['status'], 'grounded')
        self.assertEqual(result['missing'], '')
        # A single punctuation unit may itself be partially answerable.
        body = self.partial_body()
        body['coverage'] = [{'question_id': 'q1', 'claims': [0], 'missing': '资料未给出具体数量。'}]
        result = self.run_body('说明限制原则以及具体数量', self.partial['result']['citations'], body)
        self.assertEqual(result['status'], 'partial')


    def test_pure_number_question_without_a_number_is_insufficient_not_partial(self):
        # Captured live failure (issue05-live-v32, call 21 / run 54): the answer attached
        # a principle claim to a question that only asked for a count, so the derived
        # status became partial. A count-only question cannot be satisfied by a principle,
        # so the correct body leaves claims empty and derives insufficient.
        report = json.loads((ROOT / 'docs/evidence/issue05-live-v32-20260910.json').read_text(encoding='utf-8'))
        case = next(c for c in report['cases'] if c['id'] == 'number')
        record = case['result']
        with sqlite3.connect(ROOT / '.data/boundaries.sqlite3') as db:
            evidence = json.loads(db.execute('SELECT result FROM runs WHERE id=?',
                                             (record['retrieval_run_id'],)).fetchone()[0])['candidates']
        body = {'coverage': [{'question_id': 'q1', 'claims': [],
                              'missing': '资料未提供工具数量上限的具体数字。'}],
                'claims': [], 'citations': []}
        result = self.run_body(case['question'], evidence, body)
        self.assertEqual(result['status'], 'insufficient')
        self.assertEqual(result['claims'], [])
        self.assertIn('数字', result['missing'])

    def test_principled_count_question_keeps_claims_out_of_the_count_item(self):
        # A question that asks a principle and a count together is partial: the principle
        # answer belongs to q1, while q2 (the count) has no claim of its own.
        body = {'coverage': [{'question_id': 'q1', 'claims': [0], 'missing': ''},
                             {'question_id': 'q2', 'claims': [], 'missing': '资料未给出具体数量。'}],
                'claims': [{'text': '只授予完成任务所必需的工具。',
                            'citations': [self.partial['result']['citations'][0]['id']]}],
                'citations': copy.deepcopy(self.partial['result']['citations'])}
        result = self.run_body('应如何限制工具？具体最多几项？',
                               self.partial['result']['citations'], body)
        self.assertEqual(result['status'], 'partial')
        self.assertIn('具体数量', result['missing'])

    def test_empty_duplicate_unknown_and_invalid_claim_coverage_rejected(self):
        valid = {'question_id': 'q1', 'claims': [0], 'missing': ''}
        for rows in ([], [valid, valid], [{**valid, 'question_id': 'q2'}],
                     [{**valid, 'claims': [99]}], [{**valid, 'claims': [True]}],
                     [{**valid, 'claims': []}], [{**valid, 'claims': [], 'missing': '缺失'}]):
            with self.subTest(rows=rows):
                body = json.loads(self.conditions['record']['model_output'])
                body['coverage'] = rows
                with self.assertRaisesRegex(ValueError, '问题覆盖'):
                    self.run_body(self.conditions['retrieval']['query'], self.conditions['retrieval']['candidates'], body)
