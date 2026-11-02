"""Parent-owned held-out validation for malformed encodings."""
import unittest
from query import parse_query


class QueryEncodingValidation(unittest.TestCase):
    def test_invalid_hex_escape(self):
        for query in ("a=%ZZ", "a=%", "a=%C", "%Q0=x"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                parse_query(query)

    def test_invalid_utf8(self):
        for query in ("a=%FF", "a=%C3", "a=%C3%28"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                parse_query(query)
