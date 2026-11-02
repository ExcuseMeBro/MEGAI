"""Parent-owned public-contract checks for query parsing."""
import unittest
from query import parse_query


class QueryAcceptance(unittest.TestCase):
    def test_empty_and_prefix(self):
        self.assertEqual(parse_query(""), [])
        self.assertEqual(parse_query("?"), [])
        self.assertEqual(parse_query("?a=1"), [("a", "1")])

    def test_repeated_keys_and_order(self):
        self.assertEqual(parse_query("a=1&b=2&a=3"), [("a", "1"), ("b", "2"), ("a", "3")])

    def test_plus_and_utf8(self):
        self.assertEqual(parse_query("x=a+b&y=%C3%A9"), [("x", "a b"), ("y", "é")])

    def test_literal_equal_and_encoded_separator(self):
        self.assertEqual(parse_query("a=x=y&b=c%26d"), [("a", "x=y"), ("b", "c&d")])

    def test_empty_fields(self):
        self.assertEqual(parse_query("=v&a="), [("", "v"), ("a", "")])

    def test_missing_equal_or_empty_piece(self):
        for query in ("a", "a=1&&b=2", "a=1&", "&a=1"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                parse_query(query)
