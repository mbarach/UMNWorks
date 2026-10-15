"""Pair Works items with resume items. CLI: python3 -I scripts/match.py AUDIT_DIR -> AUDIT_DIR/matches.json"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import items as I

MATCH_KINDS = {"publication", "presentation", "honor", "service", "grant"}
YEAR_SLACK = {"publication": 1, "presentation": 0, "honor": 0, "service": 99, "grant": 1}
TITLE_KINDS = {"publication", "honor", "grant"}     # compare titles; others compare venues
# publication titles get truncated and presentation venues abbreviated, so those use containment; the rest use Jaccard,
# which keeps "Strategic Management Journal" apart from "Journal of Strategy and Management".
CONTAINMENT_KINDS = {"publication", "presentation"}
THRESHOLD = {"publication": 0.5, "presentation": 0.5, "honor": 0.6, "service": 0.6, "grant": 0.6}

def expand_aliases(text, aliases):
    t = I.norm_text(text)
    for short, full in sorted(aliases.items(), key=lambda kv: -len(kv[0])):
        t = re.sub(r"(?<![a-z0-9])" + re.escape(I.norm_text(short)) + r"(?![a-z0-9])", I.norm_text(full), t)
    return t

def _key_text(it, aliases):
    if it["kind"] in TITLE_KINDS and it["title"]:
        return expand_aliases(it["title"], aliases)
    return expand_aliases(it["venue"] or it["title"], aliases)

def similarity(a, b, aliases):
    ta, tb = I.tokens(_key_text(a, aliases)), I.tokens(_key_text(b, aliases))
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    if a["kind"] in CONTAINMENT_KINDS:
        return inter / min(len(ta), len(tb))      # "SMS San Francisco" vs "SMS Annual Conference San Francisco"
    s = inter / len(ta | tb)
    if a["kind"] == "service":                    # same venue, different role (reviewer vs editorial board): rank below a role match
        ra, rb = I.tokens(a["title"]), I.tokens(b["title"])
        if ra and rb and not (ra & rb):
            s *= 0.75
    return s

def _rank(score, w, r):
    """Sort key: best score first, then an exact year match, then a known year over a null one, then ids in numeric order."""
    exact = 1 if (w["year"] is not None and r["year"] is not None and w["year"] == r["year"]) else 0
    known = 1 if r["year"] is not None else 0
    num = int(r["id"][1:]) if r["id"][1:].isdigit() else 0
    return (-score, -exact, -known, num, w["id"])

def _year_ok(a, b):
    if a["year"] is None or b["year"] is None:
        return True
    return abs(a["year"] - b["year"]) <= YEAR_SLACK[a["kind"]]

def match_items(works, resume, aliases, threshold=None):
    works = [w for w in works if w["kind"] in MATCH_KINDS]
    resume = [r for r in resume if r["kind"] in MATCH_KINDS]
    pairs = []
    for w in works:
        for r in resume:
            if w["kind"] != r["kind"] or not _year_ok(w, r):
                continue
            s = similarity(w, r, aliases)
            if s >= (threshold if threshold is not None else THRESHOLD[w["kind"]]):
                pairs.append((s, w, r))
    pairs.sort(key=lambda p: _rank(*p))
    used_w, used_r, matched = set(), set(), []
    for s, w, r in pairs:
        wid, rid = w["id"], r["id"]
        if wid in used_w or rid in used_r:
            continue
        used_w.add(wid); used_r.add(rid)
        matched.append({"works": wid, "resume": rid, "score": round(s, 3)})
    return {"matched": matched,
            "resume_only": [r["id"] for r in resume if r["id"] not in used_r],
            "works_only": [w["id"] for w in works if w["id"] not in used_w]}

def main(audit_dir):
    d = pathlib.Path(audit_dir)
    aliases = json.loads(pathlib.Path(__file__).with_name("aliases.json").read_text(encoding="utf-8"))
    works = I.load_items(d / "works_items.json"); resume = I.load_items(d / "resume_items.json")
    m = match_items(works, resume, aliases)
    (d / "matches.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    print(f"matched={len(m['matched'])} resume_only={len(m['resume_only'])} works_only={len(m['works_only'])}")

if __name__ == "__main__":
    main(sys.argv[1])
