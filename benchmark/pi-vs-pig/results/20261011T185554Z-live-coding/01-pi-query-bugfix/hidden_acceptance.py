import unittest
from query import parse_query
from urllib.parse import unquote_plus
class Acceptance(unittest.TestCase):
    def test_empty(self): self.assertEqual(parse_query(''), {})
    def test_question(self): self.assertEqual(parse_query('?a=1'), {'a':['1']})
    def test_only_one_question_removed(self): self.assertEqual(parse_query('??a=1'), {'?a':['1']})
    def test_repeated(self): self.assertEqual(parse_query('a=1&b=2&a=3'), {'a':['1','3'], 'b':['2']})
    def test_flag(self): self.assertEqual(parse_query('flag'), {'flag':['']})
    def test_blank(self): self.assertEqual(parse_query('a=&a&b='), {'a':['',''], 'b':['']})
    def test_empty_key(self): self.assertEqual(parse_query('=x&=y'), {'':['x','y']})
    def test_equals(self): self.assertEqual(parse_query('a=b=c'), {'a':['b=c']})
    def test_separators(self): self.assertEqual(parse_query('&&a=1&&'), {'a':['1']})
    def test_encoded_key(self): self.assertEqual(parse_query('a%20b=x&a+b=y'), {'a b':['x','y']})
    def test_encoded_separators(self): self.assertEqual(parse_query('q=a%26b%3Dc'), {'q':['a&b=c']})
    def test_unicode(self): self.assertEqual(parse_query('q=%E4%BD%A0%E5%A5%BD'), {'q':['你好']})
    def test_plus_literal(self): self.assertEqual(parse_query('x=%2B+%252B'), {'x':['+ %2B']})
    def test_bad_percent(self):
        for s in ['%', '%2', '%GG', '%FF', '%E4%A0']:
            self.assertEqual(parse_query('q='+s), {'q':[unquote_plus(s)]})
    def test_semicolon_literal(self): self.assertEqual(parse_query('a=1;b=2'), {'a':['1;b=2']})
    def test_encoded_duplicate(self): self.assertEqual(parse_query('a=1&%61=2'), {'a':['1','2']})
