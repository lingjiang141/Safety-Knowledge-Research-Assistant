import argparse
import json
import sqlite3
import sys
import os
import getpass
from pathlib import Path
from datetime import date

from .store import Store
from .answer import Ledger, answer, validate


def main(argv=None):
    # Windows redirected output can otherwise use the legacy system code page.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="安全知识研究助手：检索与受预算保护的回答")
    parser.add_argument("--db", default=".data/knowledge.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser("import")
    ingest.add_argument("file")
    for flag in ("title", "source", "license"):
        ingest.add_argument("--" + flag, required=True)
    ingest.add_argument("--acquired", default=date.today().isoformat())
    search = commands.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--retrieval", choices=["keyword", "vector"], default="keyword")
    commands.add_parser("index", help="重建本地向量索引")
    commands.add_parser("docs")
    commands.add_parser("read").add_argument("chunk_id")
    commands.add_parser("run").add_argument("run_id", type=int)
    commands.add_parser("replay", help="离线重放已保存的失败正文，不联网").add_argument("run_id", type=int)
    ask = commands.add_parser("ask")
    ask.add_argument("query")
    ask.add_argument("--demo", action="store_true", help="无网络模拟输出，不代表真实答案")
    ask.add_argument("--config", help="本机核实的模型与价格 JSON，不包含密钥")
    ask.add_argument("--preflight", action="store_true", help="只查看请求和最大费用预留，不联网")
    ask.add_argument("--prompt-key", action="store_true", help="在当前终端隐藏输入密钥，不保存")
    ask.add_argument("--retrieval", choices=["keyword", "vector"], default="keyword")
    commands.add_parser("budget")
    args = parser.parse_args(argv)
    store = None
    ledger = None
    try:
        store = Store(args.db)
        vector = None
        if args.command == "index" or getattr(args,"retrieval",None) == "vector":
            from .vector import VectorSearch
            vector = VectorSearch(store)
        if args.command in ("ask", "budget"):
            # Independent of --db: changing knowledge DB must not reset spend.
            ledger = Ledger(Path(__file__).resolve().parents[1] / ".data" / "budget.sqlite3")
            if args.command == "budget":
                result = ledger.summary()
            else:
                config = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else None
                key = os.environ.get("DEEPSEEK_API_KEY")
                if args.prompt_key and not args.demo and not args.preflight:
                    if not sys.stdin.isatty():
                        raise ValueError("隐藏输入密钥需在交互终端运行。")
                    key = getpass.getpass("DeepSeek API key（隐藏输入、不保存）：")
                result = answer(store, args.query, ledger, config=config,
                                key=key, demo=args.demo, preflight=args.preflight,
                                search=vector.search if vector else None)
        elif args.command == "index":
            result = vector.build()
        elif args.command == "import":
            result = store.ingest(args.file, args.title, args.source, args.license, args.acquired)
        elif args.command == "search":
            result = (vector.search if vector else store.search)(args.query, args.limit)
        elif args.command == "docs":
            result = store.documents()
        elif args.command == "read":
            result = store.read(args.chunk_id)
        elif args.command == "replay":
            record = store.run(args.run_id)
            if not isinstance(record.get("model_output"), str):
                raise ValueError("此记录没有可重放的模型正文；旧版失败记录无法还原。")
            evidence = store.run(record["retrieval_run_id"])["candidates"]
            result = {"mode": "offline-replay", "network_called": False,
                      "original_diagnostic": record.get("diagnostic"),
                      "answer": validate(json.loads(record["model_output"]), evidence,
                                         record.get("questions") if record.get("prompt_version") in {"evidence-v3", "evidence-v3.1", "evidence-v3.2", "evidence-v3.3", "evidence-v3.4"} else None)}
        else:
            result = store.run(args.run_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 2
    finally:
        if store:
            store.close()
        if ledger:
            ledger.close()
