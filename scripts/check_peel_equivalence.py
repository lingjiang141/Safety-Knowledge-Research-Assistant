"""Prove peel_metadata() == the two inline copies it replaced (Issue 14 follow-up).

Run over an exhaustive set of synthetic title blocks, comparing the shared function
against faithful reconstructions of the pre-extraction structured and procedure
copies. Any behavioural drift shows as a mismatch.
"""
import itertools
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skra.store import peel_metadata, is_metadata_block, META_LINE, ADAPT_NOTE, METADATA_SECTION


def original(lines, units):
    """Verbatim pre-extraction copy (structured variant; procedure differed only in
    the loop variable names, which cannot change behaviour)."""
    peeled = []
    for section, start, end in units:
        block = lines[start - 1:end]
        if is_metadata_block("\n".join(block)):
            peeled.append((section, start, end))
            continue
        head = re.match(r"^#{1,6}\s+(.+)$", block[0]) if block else None
        if not head:
            peeled.append((section, start, end))
            continue
        body_offset = None
        for i in range(1, len(block)):
            line = block[i]
            if not line.strip() or META_LINE.match(line) or ADAPT_NOTE.match(line):
                continue
            body_offset = i
            break
        if body_offset is None:
            nonblank = [l for l in block[1:] if l.strip()]
            if nonblank and all(not l.strip() or META_LINE.match(l) or ADAPT_NOTE.match(l)
                                for l in block[1:]):
                peeled.append((METADATA_SECTION, start, end))
            else:
                peeled.append((section, start, end))
            continue
        region = block[1:body_offset]
        has_meta = any(META_LINE.match(l) or ADAPT_NOTE.match(l) for l in region)
        if has_meta and all(not l.strip() or META_LINE.match(l) or ADAPT_NOTE.match(l)
                            for l in region):
            peeled.append((METADATA_SECTION, start, start + body_offset - 1))
            peeled.append((section, start + body_offset, end))
        else:
            peeled.append((section, start, end))
    return peeled


BODIES = [
    "",                                  # heading only
    "\n",                                # heading then blank
    "\nSource: x\nLicense: y\n",         # heading + pure boilerplate
    "\nSource: x\nLicense: y\n\nreal body\n",
    "\nThis is a selected excerpt, not the complete document.\n",
    "\nreal body starts here\n",
    "\nNote: adaption note\n\nreal body\n",
    "\n\n\nreal body after blanks\n",
    "immediate body (no blank line)\n",
]
HEADS = ["# Title", "## Section", "### Deep", "no heading at all", "", "####"]
SECTIONS = ["(正文)", "Title", "Section"]


def main():
    cases, mismatches = 0, 0
    for head, body, section in itertools.product(HEADS, BODIES, SECTIONS):
        text = head + body
        lines = text.splitlines()
        if not lines:
            continue
        units = [(section, 1, len(lines))]
        # Some cases end with a trailing newline: mirror str.splitlines() semantics.
        got, want = peel_metadata(lines, units), original(lines, units)
        cases += 1
        if got != want:
            mismatches += 1
            print(f"MISMATCH head={head!r} body={body!r} sec={section!r}")
            print(f"  got : {got}")
            print(f"  want: {want}")
    # Multi-unit inputs: metadata peeling must not disturb later units.
    lines = "# T\n\nSource: x\nLicense: y\n\n## A\n\nbody A\n\n## B\n\nbody B".splitlines()
    units = [("T", 1, 5), ("A", 6, 8), ("B", 9, 11)]
    got, want = peel_metadata(lines, units), original(lines, units)
    cases += 1
    if got != want:
        mismatches += 1
        print("MULTI-UNIT MISMATCH")
        print("  got :", got)
        print("  want:", want)
    print(f"\n{cases} cases compared, {mismatches} mismatches")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
