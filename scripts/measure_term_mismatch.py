"""Measure the Chinese-query / English-corpus term mismatch (Issue 08 criterion 2)."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from skra.store import ALIASES, Store  # noqa: E402
from skra.eval import load_cases  # noqa: E402

TOKEN = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]+")


def is_cjk(text):
    return all("\u4e00" <= ch <= "\u9fff" for ch in text)


def main():
    store = Store(".data/knowledge.sqlite3")
    cases = load_cases("examples/eval-dev-cases.json", kind="development")
    zero = []
    print(f"{'用例':6s} {'中':>3s} {'英':>3s} {'别名':>4s} {'候选':>4s} {'标注束':>6s}")
    for case in cases:
        query = case.question
        expanded = query.lower()
        alias_hit = [t for t in ALIASES if t in query]
        for term, english in ALIASES.items():
            if term in query:
                expanded += " " + english
        tokens = TOKEN.findall(expanded)
        cjk = [t for t in tokens if is_cjk(t)]
        non = [t for t in tokens if not is_cjk(t)]
        count = len(store.search(query, 5)["candidates"])
        if count == 0:
            zero.append(case.id)
        print(f"{case.id:6s} {len(cjk):>3d} {len(non):>3d} "
              f"{str(bool(alias_hit)):>4s} {count:>4d} {len(case.evidence):>6d}")
    print()
    print(f"零候选用例：{zero}（{len(zero)}/{len(cases)}）")
    print()
    print("=== 零候选用例详情 ===")
    for case in cases:
        if case.id not in zero:
            continue
        expanded = case.question.lower()
        for term, english in ALIASES.items():
            if term in case.question:
                expanded += " " + english
        print(f"{case.id}: {case.question}")
        print(f"   词项: {sorted(set(TOKEN.findall(expanded)))}")
        print(f"   标注: {[(b.source, b.start_line, b.end_line) for b in case.evidence]}")
    store.close()


if __name__ == "__main__":
    main()
