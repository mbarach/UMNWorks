"""Merge the artifact's saved answers into the audit and report what is decided and what remains.

Usage: python3 merge_answers.py AUDIT_DIR
  reads  AUDIT_DIR/audit.json and AUDIT_DIR/answers/answers/<recordId>.json (from ArtifactData list with out_dir)
  writes AUDIT_DIR/decisions.json  {recordId: {screen, title, answers:{...}, remaining:[fields]}}
"""
import json, sys, pathlib
d = pathlib.Path(sys.argv[1])
audit = {r["id"]: r for r in json.loads((d / "audit.json").read_text())}
answers = {}
for p in (d / "answers" / "answers").glob("*.json"):
    doc = json.loads(p.read_text())
    data = doc.get("data", doc)
    data.pop("updatedAt", None)
    answers[p.stem] = data
out, remaining = {}, []
for rid, r in audit.items():
    a = answers.get(rid, {})
    asked = [k for k, f in r["flags"].items() if f.get("ask")]
    rem = [k for k in asked if a.get(k) in (None, "")]
    out[rid] = {"screen": r["screenName"], "title": r["title"], "year": r["year"], "answers": a, "remaining": rem}
    if rem:
        remaining.append((r["screenName"], r["year"], r["title"][:60], rem))
(d / "decisions.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
asked_total = sum(1 for r in audit.values() if any(f.get("ask") for f in r["flags"].values()))
print(f"answer docs={len(answers)} records with questions={asked_total} decided={asked_total-len(remaining)} remaining={len(remaining)}")
for s, y, t, rem in sorted(remaining):
    print(f"  {s[:28]:28} {y} {t:60} needs {', '.join(rem)}")
touched = sum(1 for a in answers.values() if "teaching" in a)
print(f"teaching toggles touched={touched}; end dates entered={sum(1 for a in answers.values() if a.get('end'))}")
