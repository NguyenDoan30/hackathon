import unittest
from ai_smart_context import Source, TranscriptSegment, Turn, Settings, Result


class SchemaTests(unittest.TestCase):
    def test_document_and_transcript_inputs(self):
        document = Source('doc-1', 'lesson-1', 'Tài liệu', text='SQLite là một hệ quản trị.')
        transcript = Source('lecture-1', 'lesson-1', 'Bài giảng', kind='transcript',
                            segments=(TranscriptSegment('SQLite giúp truy vấn.', 135, 155),))
        self.assertEqual(document.lesson_id, transcript.lesson_id)
        self.assertEqual(transcript.segments[0].start_seconds, 135)

    def test_missing_source_identity_rejected(self):
        for field in ('id', 'lesson_id', 'title'):
            values = dict(id='doc-1', lesson_id='lesson-1', title='Tài liệu', text='SQLite')
            values[field] = ' '
            with self.subTest(field=field), self.assertRaises(ValueError):
                Source(**values)

    def test_empty_source_rejected(self):
        with self.assertRaises(ValueError):
            Source('doc-1', 'lesson-1', 'Tài liệu')

    def test_invalid_source_kind_rejected(self):
        with self.assertRaises(ValueError):
            Source('doc-1', 'lesson-1', 'Tài liệu', text='SQLite', kind='unknown')

    def test_document_cannot_claim_audio_segments(self):
        with self.assertRaises(ValueError):
            Source('doc-1', 'lesson-1', 'Tài liệu', segments=(TranscriptSegment('SQLite', 0),))

    def test_invalid_audio_timestamps_rejected(self):
        for value in (-1, True, float('nan'), float('inf'), '02:15'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                TranscriptSegment('SQLite', value)

    def test_reversed_audio_interval_rejected(self):
        with self.assertRaises(ValueError):
            TranscriptSegment('SQLite', 155, 135)

    def test_history_role_and_lesson_required(self):
        for values in (('system', 'SQLite', 'lesson-1'), ('user', '', 'lesson-1'), ('user', 'SQLite', '')):
            with self.subTest(values=values), self.assertRaises(ValueError):
                Turn(*values)

    def test_oversized_source_rejected(self):
        with self.assertRaises(ValueError):
            Source('doc-1', 'lesson-1', 'Tài liệu', text='x' * 1_000_001)

    def test_invalid_budgets_rejected(self):
        for values in ({'chunk_chars':1000,'overlap_chars':1000}, {'context_chars':999},
                       {'timeout_seconds':0}, {'retries':4}, {'top_k':0}, {'max_summary_batches':0}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                Settings(**values)

    def test_result_serialization_keeps_optional_timestamp(self):
        result = Result('ok', answer='SQLite', citations=[{'source_id':'doc-1', 'start_seconds':None}], provider='mock', simulated=True)
        data = result.to_dict()
        self.assertTrue(data['simulated'])
        self.assertIsNone(data['citations'][0]['start_seconds'])
