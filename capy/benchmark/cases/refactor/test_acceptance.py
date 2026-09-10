import unittest

from reporting import render_checks


class ReportAcceptance(unittest.TestCase):
    def test_default_text(self):
        self.assertEqual(
            render_checks([("lint", "pass"), ("unit", "fail"), ("network", "skip")]),
            "PASS lint\nFAIL unit\nSKIP network\nTOTAL 3 | PASS 1 | FAIL 1 | SKIP 1",
        )

    def test_empty_text(self):
        self.assertEqual(render_checks([]), "TOTAL 0 | PASS 0 | FAIL 0 | SKIP 0")

    def test_empty_json(self):
        self.assertEqual(
            render_checks([], "json"),
            '{"checks":[],"fail":0,"pass":0,"skip":0,"total":0}',
        )

    def test_exact_json_counts_and_order(self):
        self.assertEqual(
            render_checks([("z", "skip"), ("a", "pass"), ("a", "fail")], "json"),
            '{"checks":[{"name":"z","status":"skip"},{"name":"a","status":"pass"},'
            '{"name":"a","status":"fail"}],"fail":1,"pass":1,"skip":1,"total":3}',
        )

    def test_duplicate_names_and_repeated_statuses(self):
        self.assertEqual(
            render_checks(
                [("same", "pass"), ("same", "pass"), ("same", "skip")], "text"
            ),
            "PASS same\nPASS same\nSKIP same\nTOTAL 3 | PASS 2 | FAIL 0 | SKIP 1",
        )

    def test_empty_and_unicode_names_text(self):
        self.assertEqual(
            render_checks([("", "fail"), ("o‘zbek 🐾", "pass")]),
            "FAIL \nPASS o‘zbek 🐾\nTOTAL 2 | PASS 1 | FAIL 1 | SKIP 0",
        )

    def test_json_escaping_and_unicode(self):
        self.assertEqual(
            render_checks([('é"\\\n', "pass")], "json"),
            '{"checks":[{"name":"é\\"\\\\\\n","status":"pass"}],'
            '"fail":0,"pass":1,"skip":0,"total":1}',
        )

    def test_unknown_status_rejected_in_both_styles(self):
        for style in ["text", "json"]:
            for status in ["PASS", "", "unknown"]:
                with (
                    self.subTest(style=style, status=status),
                    self.assertRaises(ValueError),
                ):
                    render_checks([("valid", "pass"), ("invalid", status)], style)

    def test_unknown_style_rejected(self):
        for style in ["", "TEXT", "yaml"]:
            with self.subTest(style=style), self.assertRaises(ValueError):
                render_checks([], style)

    def test_nonmutation_in_both_styles(self):
        for style in ["text", "json"]:
            source = [("z", "fail"), ("a", "pass"), ("z", "skip")]
            render_checks(source, style)
            self.assertEqual(source, [("z", "fail"), ("a", "pass"), ("z", "skip")])


if __name__ == "__main__":
    unittest.main()
