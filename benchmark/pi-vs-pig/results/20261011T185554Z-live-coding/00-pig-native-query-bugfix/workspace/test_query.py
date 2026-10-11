import unittest
from urllib.parse import unquote_plus

from query import parse_query


class ParseQueryTests(unittest.TestCase):
    def test_empty_fields_are_skipped(self):
        for query in ('', '?', '&', '?&&'):
            with self.subTest(query=query):
                self.assertEqual(parse_query(query), {})
        self.assertEqual(parse_query('?&&a=1&&b=2&'),
                         {'a': ['1'], 'b': ['2']})

    def test_only_one_leading_question_mark_is_removed(self):
        self.assertEqual(parse_query('??a=1'), {'?a': ['1']})
        self.assertEqual(parse_query('a?=1'), {'a?': ['1']})

    def test_blank_values_and_empty_keys_are_preserved(self):
        self.assertEqual(parse_query('flag&a=&=value&=&'),
                         {'flag': [''], 'a': [''], '': ['value', '']})
        self.assertEqual(parse_query('=&&='), {'': ['', '']})

    def test_fields_split_at_first_equals_only(self):
        self.assertEqual(parse_query('a=b=c&x==&='),
                         {'a': ['b=c'], 'x': ['='], '': ['']})

    def test_decoding_occurs_after_splitting(self):
        self.assertEqual(parse_query('%26%3D=%3D%26&plus=%2B+'),
                         {'&=': ['=&'], 'plus': ['+ ']})

    def test_utf8_and_plus_decoding_in_keys_and_values(self):
        self.assertEqual(parse_query('caf%C3%A9+name=%E2%98%83+%F0%9F%98%80'),
                         {'café name': ['☃ 😀']})
        self.assertEqual(parse_query('日本語=é'), {'日本語': ['é']})

    def test_repeated_decoded_keys_keep_encounter_order(self):
        self.assertEqual(parse_query('a=1&b=x&%61=2&a&a=3&b=y'),
                         {'a': ['1', '2', '', '3'], 'b': ['x', 'y']})
        self.assertEqual(parse_query('a+b=first&a%20b=second'),
                         {'a b': ['first', 'second']})

    def test_malformed_escapes_match_unquote_plus(self):
        for text in ('%', '%2', '%GG', '%FF', '%C3%28', '%E2%82', 'x+%zz%20'):
            with self.subTest(text=text):
                decoded = unquote_plus(text)
                self.assertEqual(parse_query(text + '=' + text),
                                 {decoded: [decoded]})

    def test_input_is_unchanged_and_results_are_independent(self):
        query = '?a=1&a=2'
        first = parse_query(query)
        first['a'].append('3')
        self.assertEqual(query, '?a=1&a=2')
        self.assertEqual(parse_query(query), {'a': ['1', '2']})


if __name__ == '__main__':
    unittest.main()
