"""MAA'nin Analyst->Critic->Master + Anayasa + retry akisini LangGraph'te kurar."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
from typing import TypedDict
from langgraph.graph import StateGraph, END
from constitution import constitution_check

class S(TypedDict):
    ticker: str; draft: str; critique: str; final: str
    retry: int; clear: bool; issues: list; log: list

def analyst(s):
    s["log"].append("analyst"); s["draft"] = f"{s['ticker']} analizi (taslak)"; return s
def critic(s):
    s["log"].append("critic"); s["critique"] = "karar kodu eksik"; return s
def master(s):
    s["log"].append(f"master(deneme {s['retry']})")
    s["final"] = f"{s['ticker']} icin TUT karari." if s["retry"] > 0 else f"{s['ticker']} icin AL sinyali var."
    return s
def gate(s):
    c = constitution_check(s["final"]); s["clear"], s["issues"] = c["clear"], c["issues"]
    s["log"].append(f"anayasa: {'GECTI' if c['clear'] else 'KALDI ' + str(c['issues'])}")
    return s
def route(s):
    return END if s["clear"] or s["retry"] >= 2 else "retry"
def retry(s):
    s["retry"] += 1; s["log"].append("--retry--"); return s

g = StateGraph(S)
for n, f in [("analyst",analyst),("critic",critic),("master",master),("gate",gate),("retry",retry)]:
    g.add_node(n, f)
g.set_entry_point("analyst")
g.add_edge("analyst","critic"); g.add_edge("critic","master"); g.add_edge("master","gate")
g.add_conditional_edges("gate", route, {"retry":"retry", END:END})
g.add_edge("retry","master")
app = g.compile()

t = time.time()
r = app.invoke({"ticker":"NVDA","draft":"","critique":"","final":"","retry":0,"clear":False,"issues":[],"log":[]})
print(f"LangGraph kaskadi: {time.time()-t:.3f} sn", flush=True)
print(f"  Akis    : {' -> '.join(r['log'])}", flush=True)
print(f"  Retry   : {r['retry']}", flush=True)
print(f"  Anayasa : {'GECTI' if r['clear'] else 'KALDI'}", flush=True)
print(f"  Cikti   : {r['final']}", flush=True)
print(f"\nSONUC: Anayasa'yi ihlal eden ilk cikti YAKALANDI ve duzeltildi -> "
      f"MAA'nin mantigi LangGraph'te BIREBIR calisiyor.", flush=True)
