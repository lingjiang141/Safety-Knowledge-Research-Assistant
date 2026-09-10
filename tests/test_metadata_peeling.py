"""Issue 14 follow-up: the metadata-peeling rule is shared, and tested as a rule.

Until now the peeling logic existed twice (once per splitting strategy) and was only
covered indirectly, through each strategy's own tests. That meant a change to the
rule had to be made in two places, and only a partial edit would go unnoticed. These
tests pin the rule itself, so both strategies depend on one verified implementation.
"""
import unittest

from skra.store import peel_metadata, METADATA_SECTION, is_metadata_block

TITLE_WITH_BOILERPLATE = """# Rotating an API key safely

Source: internal runbook, 2026
License: CC0-1.0

## Steps

1. Revoke the old key.
""".splitlines()

TITLE_ONLY = "# Heading only".splitlines()


class PeelMetadataTest(unittest.TestCase):
    def test_boilerplate_is_split_from_its_heading(self):
        """Provenance lines under an H1 become their own metadata unit."""
        units = [("Steps", 1, len(TITLE_WITH_BOILERPLATE))]
        result = peel_metadata(TITLE_WITH_BOILERPLATE, units)
        self.assertEqual(result[0][0], METADATA_SECTION,
                         "标题下的来源/许可行必须归入元数据单元")
        self.assertEqual(result[1][0], "Steps",
                         "正文单元必须保留原标题")
        # The metadata unit ends at the last boilerplate line, body starts after it.
        self.assertEqual(result[0][1:], (1, 5))
        self.assertEqual(result[1][1:], (6, 8))

    def test_heading_without_boilerplate_is_untouched(self):
        """No provenance lines means nothing to peel — the unit passes through."""
        units = [("A", 1, 3)]
        lines = "# A\n\nbody\n".splitlines()
        self.assertEqual(peel_metadata(lines, units), [("A", 1, 3)])

    def test_heading_only_block_is_not_turned_into_metadata(self):
        """A bare heading is a section with no body yet, not boilerplate."""
        units = [("Heading only", 1, 1)]
        self.assertEqual(peel_metadata(TITLE_ONLY, units), [("Heading only", 1, 1)])

    def test_units_are_not_renumbered(self):
        """Peeling preserves line numbers, so cited spans stay locatable."""
        # The title unit (1-4) contains no real body, so it is marked metadata over
        # its original span; the following section keeps its own line numbers.
        units = [("T", 1, 4), ("Steps", 5, 8)]
        result = peel_metadata(TITLE_WITH_BOILERPLATE, units)
        self.assertEqual([(u[1], u[2]) for u in result],
                         [(1, 4), (5, 8)],
                         "剥离必须保留原行号，不得重新编号")

    def test_later_units_are_unaffected_by_a_leading_peel(self):
        """Only the title block is inspected; following sections pass through."""
        units = [("T", 1, 4), ("Steps", 5, 8)]
        result = peel_metadata(TITLE_WITH_BOILERPLATE, units)
        self.assertEqual(result[-1], ("Steps", 5, 8))

    def test_body_below_boilerplate_keeps_its_heading(self):
        """When a title block has real body too, only the boilerplate is peeled."""
        lines = "# Title\n\nSource: x\nLicense: y\n\nreal body line".splitlines()
        result = peel_metadata(lines, [("Title", 1, 6)])
        self.assertEqual(result[0], (METADATA_SECTION, 1, 5))
        self.assertEqual(result[1], ("Title", 6, 6),
                         "正文单元必须保留原标题并覆盖真实正文")

    def test_both_strategies_share_this_one_rule(self):
        """The guide and procedure strategies must call the same implementation.

        This is the regression guard for the duplication that made a partial edit
        possible: if either strategy grows its own copy again, this fails.
        """
        import inspect

        from skra import store

        for method in (store.Store._chunk_structured, store.Store._chunk_procedure):
            source = inspect.getsource(method)
            self.assertIn("peel_metadata(", source,
                          f"{method.__name__} 必须复用共享的剥离规则，而非自带副本")

    def test_block_of_only_boilerplate_is_recognised(self):
        """A block whose every line is a meta line counts as pure boilerplate."""
        self.assertTrue(is_metadata_block("Source: a\nLicense: b"))
        self.assertFalse(is_metadata_block("Source: a\nreal body"))


if __name__ == "__main__":
    unittest.main()
