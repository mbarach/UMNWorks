"""Turn the page's saved answers into sync_plan.json. CLI: python3 -I scripts/read_sync_answers.py AUDIT_DIR
Answer files: AUDIT_DIR/answers/answers/<cardId>.json as saved by ArtifactData list with out_dir.
Card ids: parse-<resumeId> {keep, title?, venue?, year?}; add-<proposalId> {decision: add|skip, values: {fieldName: value}};
fill-<recordId> {intl, scale, aacsb, start, end, teaching}; review-<proposalId> {decision: keep|add_to_resume|delete_by_hand}.
"""
import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import build_plan

def load_answers(audit_dir):
    """Per-card files from ArtifactData (answers/answers/<cardId>.json) or one downloaded answers/answers.json {cardId: data}."""
    out = {}
    base = pathlib.Path(audit_dir) / "answers"
    flat = base / "answers.json"
    if flat.exists():
        for cid, data in json.loads(flat.read_text(encoding="utf-8")).items():
            data = dict(data); data.pop("updatedAt", None); out[cid] = data
    for p in (base / "answers").glob("*.json"):
        doc = json.loads(p.read_text(encoding="utf-8")); data = dict(doc.get("data", doc)); data.pop("updatedAt", None)
        out[p.stem] = data
    return out

def _fields_for(p, screen, forms):
    if screen == p["screen"] or not forms or screen not in forms:
        return p["fields"], (forms or {}).get(p["screen"], {}).get("require_one_of", [])
    return forms[screen]["fields"], forms[screen].get("require_one_of", [])

def build_sync_plan(answers, proposals, audit, forms=None):
    creates, incomplete, reviews, dropped = [], [], [], []
    for p in proposals:
        a = answers.get(("add-" if p["action"] == "create" else "review-") + p["id"])
        if not a:
            continue
        if p["action"] == "create" and a.get("decision") == "add":
            if answers.get("parse-" + p.get("resume_id", ""), {}).get("keep") is False:
                dropped.append(p["id"]); continue                     # dropped in step 1: never created
            values = a.get("values", {}); screen = a.get("screen") or p["screen"]
            fields, one_of = _fields_for(p, screen, forms)
            missing = any(f["required"] and str(values.get(f["name"], "") or "") == "" for f in fields)
            if one_of and not any(str(values.get(n, "") or "") for n in one_of):
                missing = True
            if missing:
                incomplete.append(p["id"]); continue
            creates.append({"proposal_id": p["id"], "screen": screen, "screenName": (forms or {}).get(screen, {}).get("name", p["screenName"]),
                            "values": values, "fields": fields})
        elif p["action"] == "review" and a.get("decision"):
            reviews.append({"works_id": p["works_id"], "decision": a["decision"]})
    decisions = {k[5:]: {"answers": v} for k, v in answers.items() if k.startswith("fill-")}
    fills = build_plan.fill_plan(audit, decisions)
    parse = [(k[6:], v) for k, v in answers.items() if k.startswith("parse-")]
    edited = sorted(rid for rid, v in parse if v.get("keep") and any(x in v for x in ("title", "venue", "year")))
    return {"fills": fills, "creates": creates, "reviews": reviews, "incomplete_creates": incomplete, "dropped_creates": dropped,
            "parse": {"kept": sum(1 for _, v in parse if v.get("keep") is True), "dropped": sum(1 for _, v in parse if v.get("keep") is False), "edited": edited}}

def main(audit_dir):
    d = pathlib.Path(audit_dir); load = lambda n: json.loads((d / n).read_text(encoding="utf-8"))
    forms_path = pathlib.Path(__file__).resolve().parent.parent / "screens" / "forms.json"
    plan = build_sync_plan(load_answers(d), load("proposals.json"), load("audit.json"), json.loads(forms_path.read_text(encoding="utf-8")) if forms_path.exists() else None)
    (d / "sync_plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"fills={len(plan['fills'])} creates={len(plan['creates'])} incomplete={plan['incomplete_creates']} dropped={plan['dropped_creates']} reviews={len(plan['reviews'])} parse={plan['parse']}")
    if plan["parse"]["edited"]:
        print("parse items were edited on the page; re-run match.py, rules.py and build_sync_page.py before applying:", plan["parse"]["edited"])

if __name__ == "__main__":
    main(sys.argv[1])
