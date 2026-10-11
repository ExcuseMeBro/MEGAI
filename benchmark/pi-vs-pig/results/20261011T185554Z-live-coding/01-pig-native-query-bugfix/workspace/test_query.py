import unittest
from urllib.parse import unquote_plus

from query import parse_query


class ParseQueryTests(unittest.TestCase):
    def test_empty_fields(self):
        for query in ('', '?', '&', '?&&'):
            with self.subTest(query=query):
                self.assertEqual(parse_query(query), {})
        self.assertEqual(parse_query('?&a=1&&b=2&'), {'a': ['1'], 'b': ['2']})

    def test_only_one_leading_question_mark_is_removed(self):
        self.assertEqual(parse_query('??a=1'), {'?a': ['1']})
        self.assertEqual(parse_query('a?=1?'), {'a?': ['1?']})

    def test_blank_values_and_empty_keys(self):
        self.assertEqual(
            parse_query('flag&a=&=value&=&bare'),
            {'flag': [''], 'a': [''], '': ['value', ''], 'bare': ['']},
        )

    def test_first_equals_only(self):
        self.assertEqual(parse_query('a=b=c&x=='), {'a': ['b=c'], 'x': ['=']})

    def test_utf8_and_plus_decoding(self):
        self.assertEqual(
            parse_query('%E2%98%83+caf%C3%A9=%F0%9F%98%80+%2B&literal=雪'),
            {'☃ café': ['😀 +'], 'literal': ['雪']},
        )

    def test_decode_after_splitting_and_only_once(self):
        self.assertEqual(
            parse_query('a%26b=x%3Dy%26z&%3D=%2526%252B'),
            {'a&b': ['x=y&z'], '=': ['%26%2B']},
        )

    def test_repeated_decoded_keys_preserve_order(self):
        self.assertEqual(
            parse_query('a=first&b=other&%61=second&a&a=last'),
            {'a': ['first', 'second', '', 'last'], 'b': ['other']},
        )

    def test_malformed_escapes_match_unquote_plus(self):
        for raw in ('%', '%2', '%GG', '%FF', '%C3%28', '%E2%82', 'a+%zz%41'):
            with self.subTest(raw=raw):
                decoded = unquote_plus(raw)
                self.assertEqual(parse_query(raw + '=' + raw), {decoded: [decoded]})

    def test_input_and_results_are_independent(self):
        query = '?a=1&a=2'
        first = parse_query(query)
        first['a'].append('changed')
        self.assertEqual(query, '?a=1&a=2')
        self.assertEqual(parse_query(query), {'a': ['1', '2']})


if __name__ == '__main__':
    unittest.main()
