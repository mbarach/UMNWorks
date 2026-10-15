"""Turn decisions.json + records.json into a write plan: only values that differ from Works now.

Usage: python3 build_plan.py AUDIT_DIR  -> writes AUDIT_DIR/plan.json and prints a summary.
plan.json: [{id, screen, screenName, title, writes: {field: value}}]
  field keys: intl ("Yes"/"No"), scale (option text), start/end (free text date as typed),
  teaching (bool), aacsb (option text). "__leave" answers and unchanged values are dropped.
"""
import json, sys, pathlib
from collections import Counter

def fill_plan(audit, dec):
    """audit: list of audit.json records; dec: {recordId: {"answers": {...}}}. Returns the write plan."""
    plan = []
    for r in audit:
        rid = r["id"]
        a = dec.get(rid, {}).get("answers", {})
        cur = r["current"]; w = {}
        for k in ("intl", "scale", "aacsb"):
            v = a.get(k)
            if v and v != "__leave" and v != cur.get(k):
                w[k] = v
        for k in ("start", "end"):
            v = a.get(k)
            if v and v != "__leave" and not cur.get(k):
                w[k] = v
        if "teaching" in a and r.get("columns", {}).get("teaching"):
            now = cur.get("teaching") == "True"
            if bool(a["teaching"]) != now:
                w["teaching"] = bool(a["teaching"])
        if w:
            plan.append({"id": rid, "screen": r["screen"], "screenName": r["screenName"], "title": r["title"][:60], "writes": w})
    return plan

def main(audit_dir):
    d = pathlib.Path(audit_dir)
    audit = json.loads((d / "audit.json").read_text())
    dec = json.loads((d / "decisions.json").read_text())
    plan = fill_plan(audit, dec)
    (d / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False))
    c = Counter(k for p in plan for k in p["writes"])
    print(f"records to edit={len(plan)} field writes={sum(c.values())} by field={dict(c)}")
    for p in plan:
        print(f"  {p['screen']} {p['id']} {p['screenName'][:22]:22} {p['title'][:40]:40} {p['writes']}")

if __name__ == "__main__":
    main(sys.argv[1])
