"""Print browser_batch action arrays for plan.json, one JSON array per chunk.
Usage: python3 gen_batches.py AUDIT_DIR TAB_ID [SCREEN_ID] [CHUNK] [SKIP_IDS...]
Requires the helper from apply_record.js to be installed in localStorage.__worksApply first.
"""
import json, sys, pathlib
d, tab = pathlib.Path(sys.argv[1]), int(sys.argv[2])
screen = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "-" else None
chunk = int(sys.argv[4]) if len(sys.argv) > 4 else 6
skip = set(sys.argv[5:])
plan = [p for p in json.loads((d / "plan.json").read_text()) if (not screen or p["screen"] == screen) and p["id"] not in skip]
base = "https://www.digitalmeasures.com/login/umn/faculty/app/activities/instruments/896/screens/"
for i in range(0, len(plan), chunk):
    acts = []
    for p in plan[i:i+chunk]:
        acts.append({"name": "navigate", "input": {"url": f"{base}{p['screen']}/records/{p['id']}?_s=0", "tabId": tab}})
        acts.append({"name": "computer", "input": {"action": "wait", "duration": 3, "tabId": tab}})
        js = f'const f=new Function("return "+localStorage.__worksApply)(); "{p["id"]} " + await f({json.dumps(p["writes"])})'
        acts.append({"name": "javascript_tool", "input": {"action": "javascript_exec", "tabId": tab, "text": js}})
    print(json.dumps(acts, separators=(",", ":")))
    print()
