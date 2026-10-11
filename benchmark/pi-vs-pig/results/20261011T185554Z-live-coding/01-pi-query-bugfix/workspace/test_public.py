import unittest
from query import parse_query
class PublicTests(unittest.TestCase):
    def test_duplicates(self):
        self.assertEqual(parse_query('a=1&a=2'), {'a': ['1', '2']})
    def test_decoding(self):
        self.assertEqual(parse_query('q=hello+world'), {'q': ['hello world']})
