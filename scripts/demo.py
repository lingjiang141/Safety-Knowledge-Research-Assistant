"""One-command, ~3-minute demo of the delivered pipeline (Issue 12).

The demo is deliberately free and offline: it needs only the standard library
plus the downloaded local model. It reads the budget summary and writes local
run records, but does not call the network or reserve/spend budget by default.
It walks the four things the project is actually for:

  1. 切分预览    what the splitter does to the same original lines;
  2. 同题前后证据 the same question, retrieved before and after the structural
                  splitter, with the ranking change shown rather than asserted;
  3. 失败复盘    保留集三例「没取全」，并说明为什么没取全（不是「资料没有」）；
  4. 边界        a query with no evidence returns an honest gap, not a guess.

Run it with the project's own venv (the vector retriever needs the local model):

    .\\.venv\\Scripts\\python.exe scripts/demo.py
    .\\.venv\\Scripts\\python.exe scripts/demo.py --live   # 付费生成，需本机密钥

Without `--live` nothing is billed; the generation step is shown as a dry-run
receipt only.
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from skra.answer import Ledger, answer  # noqa: E402
from skra.eval import load_cases, score_retrieval, resolve_span  # noqa: E402
from skra.store import Store  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DB = ROOT / ".data/knowledge.sqlite3"
DEV_CASES = ROOT / "examples/eval-dev-cases.json"
HOLDOUT_CASES = ROOT / "examples/eval-holdout-cases.json"
FIXTURE = "85772b0052029e9b3edb20fe43f7f80f896aa9c0e6703d1ff049e7b8bc8aeb97"
SPLITTERS = ("heading-lines-v1:20", "heading-block-v2", "heading-procedure-v3")
SHOWCASE = "D04"        # 展示真实命中与未命中，不预设结构切分会提升。
MISSES = ("H03", "H04", "H09")


def rule(title):
    print("\n" + "=" * 74)
    print(title)
    print("=" * 74)


def load_corpus(source_db=SOURCE_DB):
    import sqlite3
    db = sqlite3.connect(source_db)
    db.row_factory = sqlite3.Row
    docs = [dict(r) for r in db.execute(
        "SELECT title,source,license,acquired,snapshot FROM documents "
        "WHERE source LIKE 'https://%' ORDER BY source")]
    db.close()
    return docs


def materialise(docs, splitter, workdir, tag):
    store = Store(Path(workdir) / f"{tag}.sqlite3")
    for doc in docs:
        path = Path(workdir) / f"{tag}-{len(doc['source'])}.md"
        path.write_text(doc["snapshot"], encoding="utf-8")
        store.ingest(path, doc["title"], doc["source"], doc["license"],
                     doc["acquired"], splitter=splitter)
    return store


def step_split_preview(store, splitter):
    """Show what one question's neighbourhood looks like under one splitter."""
    rule(f"① 切分预览（{splitter}）")
    doc = [d for d in store.documents() if "llm062025" in d["source"]][0]
    rows = [dict(r) for r in store.db.execute(
        "SELECT start_line,end_line,kind,text FROM chunks "
        "WHERE doc_id=? AND active=1 ORDER BY start_line", (doc["id"],))]
    print(f"{doc['title']}：{len(rows)} 个片段")
    for r in rows:
        head = r["text"].replace("\n", " ")[:58]
        print(f"  L{r['start_line']:>2}-{r['end_line']:<2} [{r['kind']:>8}] {head}")


def step_before_after(docs, workdir, cases):
    """Same question, three splitters: show the rank of the annotated span."""
    rule("② 同题前后证据：同一问题，不同切分下的命中名次")
    case = next(c for c in cases if c.id == SHOWCASE)
    span = case.evidence[0]
    print(f"问题：{case.question}")
    print(f"标注答案：{span.source.rstrip('/').rsplit('/', 1)[-1]} 第 {span.start_line}–{span.end_line} 行")
    print(f"必须含：{'、'.join(span.must_include)}")
    print()
    for splitter in SPLITTERS:
        store = materialise(docs, splitter, workdir, splitter.replace(":", "-"))
        try:
            from skra.vector import Encoder, VectorSearch
            vector = VectorSearch(store, encoder=Encoder())
            vector.build()
            # Which active chunk covers the annotated span under this splitter?
            covered = resolve_span(store, span)
            covered_ids = [r["id"] for r in covered]
            result = vector.search(case.question, 5)
            ids = [c["id"] for c in result["candidates"]]
            ranks = [ids.index(cid) + 1 for cid in covered_ids if cid in ids]
            span_desc = "、".join(f"L{r['start_line']}-{r['end_line']}" for r in covered)
            whole = (len(ranks) == len(covered_ids)) if span.required_together else bool(ranks)
            got = (f"第 {', '.join(map(str, sorted(ranks)))} 名" if ranks else "未进前 5")
            if ranks and not whole:
                got += "（仅部分证据，未完整命中）"
            marker = "✅" if whole else "❌"
            print(f"  {splitter:<22} 覆盖片段 {span_desc:<10} → {marker} {got}")
        finally:
            store.close()


def step_failures(docs, workdir):
    """Report the holdout misses with the reason each one misses."""
    rule("③ 失败复盘：保留集未取全的三例（原因，不是借口）")
    store = materialise(docs, "heading-lines-v1:20", workdir, "failures")
    try:
        from skra.vector import Encoder, VectorSearch
        vector = VectorSearch(store, encoder=Encoder())
        vector.build()
        cases = load_cases(HOLDOUT_CASES, kind="holdout")
        for case in cases:
            if case.id not in MISSES:
                continue
            scored = score_retrieval(store, case, vector.search, k=5)
            ids = scored["retrieved_chunk_ids"]
            # 部分覆盖不是全落空：H03 只取到一半（0.50），H04/H09 才是 0.00。
            got = scored["retrieved_bundles"]
            total = scored["relevant_bundles"]
            reason = "覆盖片段存在但排在 5 名之后（排序未进前 5）"
            print(f"  {case.id}  recall_at_5={scored['recall_at_5']:.2f}"
                  f"（取回 {got}/{total} 个标注束）")
            cover = []
            for bundle in scored["bundles"]:
                cover.extend(bundle["covering_chunks"])
            for cid in sorted(set(cover)):
                row = store.db.execute(
                    "SELECT start_line,end_line FROM chunks WHERE id=?", (cid,)).fetchone()
                rank = ids.index(cid) + 1 if cid in ids else None
                loc = f"L{row['start_line']}-{row['end_line']}" if row else "?"
                print(f"     覆盖片段 {loc:<8} → "
                      f"{'第 %d 名' % rank if rank else '未进前 5'}")
            print(f"     结论：{case.question[:40]}…  {reason}")
            print()
    finally:
        store.close()


def step_boundary(store, ledger):
    """A question with no evidence must produce an honest gap, not a guess."""
    rule("④ 边界：无依据时如实说明缺失（不编造）")
    question = "请给出本系统上周的误操作统计。"
    print(f"问题：{question}")
    # demo=False and no key: retrieval finds nothing, so answer() stops at the
    # honest `insufficient` branch before it ever reaches the credential check.
    # This shows the real degradation shape, not a fixture.
    result = answer(store, question, ledger,
                    search=lambda q, limit=5: store.search(q, limit))
    print(f"  状态：{result['status']}")
    print(f"  结论数：{len(result['claims'])}")
    print(f"  缺失说明：{result['missing']}")
    print("  （检索不到证据时如实降级为「无结论 + 明确缺失」，不生成回答、不编造。）")


def step_generation(store, ledger, live, config_path=None):
    """Show the paid path as a receipt; only bill with --live.

    The question is in English on purpose: the local keyword retriever indexes
    the English OWASP text verbatim, so a Chinese question tokenises to zero
    overlap and yields no evidence at all. Using an English question here keeps
    the receipt about *cost*, not about an empty retrieval.
    """
    rule("⑤ 生成路径（付费需 --live）")
    question = "What is excessive agency?"
    config = json.loads(Path(config_path or
        ROOT / "examples/deepseek-flash.2026-09-09.json").read_text(encoding="utf-8"))
    # Preflight needs the verified config (to compute the reservation) but no key:
    # it stops before any network call. A key is only read under --live.
    try:
        check = answer(store, question, ledger, config, preflight=True)
    except ValueError as exc:
        if live:
            raise
        print(f"  预检不可用：{exc}")
        print("  离线演示继续；需要有效计费配置时传 --config。没有联网或计费。")
        return
    print(f"  问题：{question}")
    if "request_bytes" not in check:
        # No evidence retrieved: answer() returns the honest `insufficient` shape
        # before it can build a request. Say so plainly instead of showing a fake
        # receipt.
        print(f"  状态：{check['status']}（检索无证据，未构造请求，故无预留回执）")
        print(f"  缺失说明：{check['missing']}")
        print("  这不是故障：本地关键词检索对纯中文问句会无命中，换成可命中问题即可见回执。")
        return
    print(f"  请求字节：{check['request_bytes']}")
    print(f"  单次最大预留：{check['max_reservation_rmb']} 元")
    print(f"  预算可用：{check['budget']['available_rmb']} 元　blocked={check['budget']['blocked']}")
    print(f"  是否已配密钥：{check['key_configured']}　是否联网：{check['network_called']}")
    if not live:
        print("  未加 --live：只显示预留回执，不联网、不计费。")
        return
    import getpass
    import os
    key = os.environ.get("DEEPSEEK_API_KEY") or getpass.getpass("DeepSeek API key（隐藏输入，不保存）：")
    result = answer(store, question, ledger, config, key)
    print(f"  状态：{result['status']}")
    print(f"  运行记录：answer_run_id={result.get('answer_run_id')}"
          f"（使用本次 --db 路径执行 `python -m skra --db <路径> run <id>` 回看）")
    print("  结论：")
    for claim in result["claims"]:
        print(f"    · {claim['text']}")
    print("  证据（英文原文 + 中文释义）：")
    for c in result["citations"]:
        quote = " ".join(c["quote"].split())[:96]
        print(f"    [{c['id'][:12]}] \"{quote}\"")
        print(f"                 释义：{c['translation']}")
    print(f"  缺失说明：{result.get('missing') or '（无）'}")
    if result.get("diagnostic"):
        print(f"  诊断：{result['diagnostic']}")
    print(f"  本次费用：{result['budget']['spent_rmb']} 元（累计）")
    print("  ⚠ 请对照原文逐条人工判断：结论是否被引用支持、释义是否准确、"
          "缺的有没有如实说明、有没有擅自裁决冲突。")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="约三分钟演示：切分、检索、失败与边界")
    parser.add_argument("--live", action="store_true", help="执行付费生成（需本机密钥）")
    parser.add_argument("--db", default=str(SOURCE_DB), help="已准备的语料库")
    parser.add_argument("--config", help="已核对的本机计费配置；不会自动更新核对日期")
    args = parser.parse_args()

    if not Path(args.db).is_file():
        raise SystemExit("数据库不存在；先运行 scripts/prepare_demo.py，再用 --db 指定演示库。")
    docs = load_corpus(args.db)
    if not docs:
        raise SystemExit("工作库里没有真实资料，先导入 OWASP 快照再演示。")
    store = Store(args.db)
    ledger = Ledger(ROOT / ".data/budget.sqlite3")
    try:
        cases = load_cases(DEV_CASES)
        with tempfile.TemporaryDirectory() as workdir:
            step_split_preview(store, "heading-lines-v1:20")
            step_before_after(docs, workdir, cases)
            step_failures(docs, workdir)
        step_boundary(store, ledger)
        step_generation(store, ledger, args.live, args.config)
    finally:
        store.close()
        ledger.close()
    rule("演示结束")
    print("本演示默认全程免费：无网络调用、不计费；保留集仅用于展示「未取全」的原因。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
