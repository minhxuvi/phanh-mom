import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('review', Path(__file__).resolve().parents[1] / 'scripts/review.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class ReviewTests(unittest.TestCase):
    def proposal(self, text, edits):
        return {'source_sha256': r.sha(text), 'edits': edits, 'unresolved': []}

    def edit(self, old, new='', block='b0001'):
        return {'block': block, 'old': old, 'new': new, 'reason': 'Cáo buộc thiếu căn cứ'}

    def test_no_edits_preserve_bytes(self):
        text = '\ufeffMình thấy học phí cao.\r\n\r\n  Giữ nhịp.\r\n'
        self.assertEqual(r.apply_edits(text, self.proposal(text, [])), text)

    def test_only_requested_span_changes(self):
        text = 'Mình thấy học phí cao.\r\n\r\nA lừa đảo.\r\n\r\nVẫn muốn trao đổi.\n'
        out = r.apply_edits(text, self.proposal(text, [self.edit('A lừa đảo.', '', 'b0002')]))
        self.assertEqual(out, text.replace('A lừa đảo.', ''))

    def test_changed_source_rejected(self):
        with self.assertRaises(ValueError):
            r.apply_edits('new', self.proposal('old', []))

    def test_ambiguous_phrase_rejected(self):
        with self.assertRaises(ValueError):
            r.apply_edits('A A', self.proposal('A A', [self.edit('A')]))

    def test_overlap_rejected(self):
        text = 'A lừa đảo.'
        with self.assertRaises(ValueError):
            r.apply_edits(text, self.proposal(text, [self.edit('A lừa đảo'), self.edit('lừa đảo')]))

    def test_all_paragraphs_in_chunks(self):
        text = '\n\n'.join(['x' * 60, 'y' * 60, 'z' * 60])
        packet = r.prepare(text, chunk_chars=100)
        self.assertEqual(len(packet['chunks']), 3)
        self.assertEqual([b['text'] for c in packet['chunks'] for b in c['blocks']], ['x'*60, 'y'*60, 'z'*60])
        with self.assertRaises(ValueError):
            r.prepare('a'*101, chunk_chars=100)

    def test_no_network_in_preparation(self):
        with patch.object(r.urllib.request, 'build_opener', side_effect=AssertionError('network')):
            self.assertEqual(r.scan('Mình thích buổi chiều.')['findings'], [])
            self.assertEqual(r.prepare('Mình thích buổi chiều.')['legal_status'], 'offline_unverified')

    def test_nfd_flag_without_source_mutation(self):
        text = r.unicodedata.normalize('NFD', 'Hắn lừa đảo.')
        self.assertTrue(r.scan(text)['findings'])
        self.assertEqual(r.apply_edits(text, self.proposal(text, [])), text)

    def test_remote_endpoints_rejected(self):
        for url in ['https://api.example.com/v1/chat/completions',
                    'http://localhost:11434/v1/chat/completions',
                    'http://127.0.0.1.evil.test/v1/chat/completions',
                    'http://192.168.1.1/v1/chat/completions',
                    'http://user:pw@127.0.0.1/v1/chat/completions',
                    'http://127.0.0.1/v1/chat/completions?remote=yes']:
            with self.assertRaises(ValueError): r.local_url(url)
        self.assertTrue(r.local_url('http://127.0.0.1:11434/v1/chat/completions'))
        self.assertTrue(r.local_url('http://[::1]:11434/v1/chat/completions'))

    def test_redirect_rejected(self):
        with self.assertRaises(ValueError):
            r.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com')

    def test_no_overwrite_or_follow_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'result'
            r.save(p, 'original')
            with self.assertRaises(FileExistsError): r.save(p, 'changed')
            link = Path(tmp) / 'link'
            link.symlink_to(p)
            with self.assertRaises(FileExistsError): r.save(link, 'changed')
            self.assertEqual(p.read_text(), 'original')
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_missing_ocr_language_does_not_fallback(self):
        with patch.object(r.shutil, 'which', return_value='/test/tesseract'), patch.object(r, 'languages', return_value=['eng']):
            with self.assertRaisesRegex(ValueError, 'vie'): r.ocr('/missing', 'vie+eng')

    def test_mock_ocr_boxes_and_metadata_limit(self):
        tsv = 'level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t10\t20\t30\t40\t90\tHello\n'
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'image.png'; p.write_bytes(b'test fixture')
            with patch.object(r.shutil, 'which', side_effect=lambda x: '/test/tesseract' if x=='tesseract' else None), patch.object(r, 'languages', return_value=['eng']), patch.object(r, 'command', return_value=tsv):
                out = r.ocr(p, 'eng')
            self.assertEqual(out['words'][0]['box'], [10,20,30,40])
            self.assertEqual(out['visual_status'], 'not_reviewed')
            self.assertEqual(out['metadata']['status'], 'not_checked')

    def test_mock_run_visits_every_chunk_and_keeps_limits(self):
        a = SimpleNamespace(context='', chunk_chars=100, endpoint='http://127.0.0.1:11434/v1/chat/completions', model='fixture', timeout=1, max_tokens=200)
        text = 'x'*60 + '\n\n' + 'y'*60
        with patch.object(r, 'request_model', return_value={'edits': [], 'unresolved': []}) as call:
            result = r.run_model(text, a)
        self.assertEqual(call.call_count, 2)
        self.assertEqual(result['chunks_reviewed'], 2)
        self.assertEqual(result['legal_status'], 'offline_unverified')
        self.assertEqual(r.apply_edits(text, result), text)
        self.assertTrue(any('toàn bài' in x for x in result['unresolved']))

    def test_bad_model_json_rejected(self):
        for val in [{'edits': [], 'unresolved': [], 'safe': True}, {'edits': 'none', 'unresolved': []}, {'edits': [], 'unresolved': [1]}]:
            with self.assertRaises(ValueError): r.validate_response(val, {})

    def test_diff_not_legal_score(self):
        result = r.diff_report('abc', 'adc')
        self.assertEqual(result['removed_or_replaced_chars'], 1)
        self.assertEqual(result['inserted_or_replacement_chars'], 1)
        self.assertNotIn('risk_score', result)


if __name__ == '__main__': unittest.main()
