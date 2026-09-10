"""Small development smoke benchmark; no generation and no paid API calls."""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from skra.store import Store
from skra.vector import VectorSearch

root=Path(__file__).resolve().parents[1]
store=Store(root/'.data/vector-baseline.sqlite3')
try:
    for filename,title,url in [
        ('owasp-prompt-injection.md','OWASP Prompt Injection excerpt','https://genai.owasp.org/llmrisk/llm01-prompt-injection/'),
        ('owasp-excessive-agency.md','OWASP Excessive Agency excerpt','https://genai.owasp.org/llmrisk/llm062025-excessive-agency/')]:
        store.ingest(root/'examples/corpus'/filename,title,url,'CC BY-SA 4.0','2026-09-09')
    engine=VectorSearch(store)
    build=engine.build()
    rows=[]
    for question,section in [('从网页或文件进入模型的恶意指令属于哪种注入？','Indirect Prompt Injections'),
                             ('应该给智能助手配备多少工具？','Minimize extensions')]:
        result=engine.search(question,5)
        target=[r['id'] for r in store.db.execute('SELECT id FROM chunks WHERE section=?',(section,))]
        ids=[c['id'] for c in result['candidates']]
        rows.append({'question':question,'expected_section':section,'relevant_ids':target,
                     'recall_at_5':len(set(target)&set(ids))/len(target), 'result':result})
    report={'kind':'development-smoke-not-held-out','generation':'not-run','paid_calls':0,
            'build':build,'documents':store.documents(),'cases':rows}
    out=root/'docs/vector-baseline.json'
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(out)
    for r in rows: print(r['expected_section'],r['recall_at_5'],r['result']['candidates'][0]['section'])
finally: store.close()
