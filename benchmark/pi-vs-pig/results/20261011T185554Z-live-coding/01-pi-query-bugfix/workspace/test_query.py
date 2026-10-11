import unittest
from urllib.parse import unquote_plus

from query import parse_query


class ParseQueryTests(unittest.TestCase):
    def test_empty_fields_and_optional_prefix(self):
        for query in ('', '?', '&', '?&&'):
            with self.subTest(query=query):
                self.assertEqual(parse_query(query), {})
        self.assertEqual(parse_query('?&a=1&&b=2&'),
                         {'a': ['1'], 'b': ['2']})

    def test_only_one_leading_question_mark_is_removed(self):
        self.assertEqual(parse_query('??a=1'), {'?a': ['1']})
        self.assertEqual(parse_query('a=?b'), {'a': ['?b']})

    def test_blank_values_and_empty_keys(self):
        self.assertEqual(parse_query('a&a=&=x&=&bare'),
                         {'a': ['', ''], '': ['x', ''], 'bare': ['']})

    def test_split_only_at_first_equals(self):
        self.assertEqual(parse_query('a=b=c&==x'),
                         {'a': ['b=c'], '': ['=x']})

    def test_decode_keys_and_values_after_splitting(self):
        self.assertEqual(
            parse_query('caf%C3%A9+key=%E2%98%83+tea&%26%3D=%26%3D%2B'),
            {'café key': ['☃ tea'], '&=': ['&=+']},
        )

    def test_duplicates_are_grouped_after_decoding_in_encounter_order(self):
        self.assertEqual(parse_query('a=1&b=x&%61=2&a=&a=3'),
                         {'a': ['1', '2', '', '3'], 'b': ['x']})

    def test_malformed_escapes_match_unquote_plus(self):
        for raw in ('%', '%2', '%GG', '%FF', '%C3%28', '%E2%82', 'x+%zz'):
            with self.subTest(raw=raw):
                decoded = unquote_plus(raw)
                self.assertEqual(parse_query(raw + '=' + raw),
                                 {decoded: [decoded]})

    def test_input_unchanged_and_results_independent(self):
        query = '?a=1&a=2'
        result = parse_query(query)
        result['a'].append('3')
        self.assertEqual(query, '?a=1&a=2')
        self.assertEqual(parse_query(query), {'a': ['1', '2']})


if __name__ == '__main__':
    unittest.main()
