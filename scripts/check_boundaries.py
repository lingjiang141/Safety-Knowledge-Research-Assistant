"""Prepare or run generation-only development cases with one hidden key prompt."""
import argparse
import getpass
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skra.answer import answer, Ledger
from skra.boundaries import load_cases, prepare
from skra.store import Store

def main():
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--config',default='examples/deepseek-flash.2026-09-09.json')
    parser.add_argument('--case',action='append',help='只运行指定 case id，可重复')
    args=parser.parse_args()
    cases=load_cases()
    if args.case:
        unknown=set(args.case)-{c['id'] for c in cases}
        if unknown: parser.error('Unknown case ID')
        cases=[c for c in cases if c['id'] in args.case]
    root=Path(__file__).resolve().parents[1]
    store=Store(root/'.data/boundaries.sqlite3')
    ledger=Ledger(root/'.data/budget.sqlite3')
    report={'mode':'live' if args.live else 'prepared-no-api', 'evidence_mode':'controlled-not-retrieval',
            'human_review':'pending', 'cases':[], 'complete':False}
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    dest=root/f'.data/boundary-report-{stamp}.json'
    try:
        config=json.loads(Path(args.config).read_text(encoding='utf-8')) if args.live else None
        prepared=[(c,prepare(store,root/'.data/boundary-fixtures',c)) for c in cases]
        if args.live:
            # Validate configuration and available budget before asking for a secret.
            case,(_,search)=prepared[0]
            check=answer(store,case['question'],ledger,config,preflight=True,search=search)
            if not check['budget_ready']: raise ValueError('预算不足或存在未结算请求。')
            key=os.environ.get('DEEPSEEK_API_KEY')
            if not key:
                if not sys.stdin.isatty(): raise ValueError('请在交互终端隐藏输入密钥。')
                key=getpass.getpass('DeepSeek API key（隐藏输入、本次进程内使用）：')
        else: key=None
        for case,(_,search) in prepared:
            row={'id':case['id'],'question':case['question'],'expected_status':case['expected_status'],
                 'human_review':case['human_review'], 'review_result':'pending'}
            report['cases'].append(row)
            if args.live:
                try:
                    result=answer(store,case['question'],ledger,config,key,search=search)
                    row['result']=result
                    row['status_matches']=result['status']==case['expected_status']
                except ValueError as exc:
                    row['error']=str(exc)
                    break
            else: row['state']='prepared-not-executed'
        report['preparation_complete']=len(prepared)==len(cases)
        report['complete']=args.live and len(report['cases'])==len(cases) and all('error' not in r for r in report['cases'])
    except (OSError,ValueError) as exc:
        report['error']=str(exc)
    finally:
        report['budget']=ledger.summary()
        dest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        store.close();ledger.close()
    print(json.dumps(report,ensure_ascii=False,indent=2))
    print('Report:',dest)
    return 2 if 'error' in report or any('error' in r for r in report['cases']) else 0

if __name__=='__main__': raise SystemExit(main())
