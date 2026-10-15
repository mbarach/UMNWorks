"""Apply the Works guideline rules to matched/unmatched items -> proposals.json (create and review cards).
Fill cards for matched records come from audit.json (build_audit.py) and are not produced here.
CLI: python3 -I scripts/rules.py AUDIT_DIR
"""
import json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import items as I

MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
US_STATES = {"alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware","florida","georgia","hawaii","idaho","illinois",
             "indiana","iowa","kansas","kentucky","louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi","missouri","montana",
             "nebraska","nevada","new hampshire","new jersey","new mexico","new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania",
             "rhode island","south carolina","south dakota","tennessee","texas","utah","vermont","virginia","washington","west virginia","wisconsin","wyoming",
             "district of columbia","puerto rico"}
US_CODES = {"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH",
            "NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC","PR"}
US_WORDS = {"usa", "u s a", "united states", "united states of america"}
COUNTRIES = {"canada","mexico","brazil","argentina","chile","colombia","peru","bolivia","uruguay","united kingdom","uk","england","scotland","wales","ireland",
             "france","germany","spain","portugal","italy","netherlands","belgium","switzerland","austria","denmark","sweden","norway","finland","iceland",
             "poland","czech republic","czechia","hungary","greece","turkey","israel","egypt","south africa","nigeria","kenya","morocco","india","china",
             "japan","south korea","korea","taiwan","singapore","hong kong","australia","new zealand","russia","ukraine","thailand","vietnam","malaysia",
             "indonesia","philippines","pakistan","saudi arabia","united arab emirates","uae","qatar","luxembourg","estonia","latvia","lithuania","slovenia",
             "croatia","romania","bulgaria","serbia","cyprus","malta","costa rica","panama","cuba","dominican republic","puerto rico"}
NON_US_CITIES = {"london","paris","berlin","munich","vienna","zurich","geneva","amsterdam","rotterdam","brussels","copenhagen","stockholm","oslo","helsinki",
                 "madrid","barcelona","lisbon","rome","milan","bologna","dublin","edinburgh","oxford","cambridge uk","toronto","montreal","vancouver","ottawa",
                 "tokyo","seoul","beijing","shanghai","hong kong","singapore","sydney","melbourne","tel aviv","jerusalem","haifa","mumbai","delhi","bangalore",
                 "sao paulo","rio de janeiro","buenos aires","santiago","lima","bogota","mexico city","fontainebleau","lausanne","st gallen","mannheim","prague",
                 "warsaw","budapest","athens","istanbul","dubai","cape town","auckland"}
STATUS_OPTION = {"published": "Published", "accepted": "Accepted", "revise-and-resubmit": "Revising to Resubmit", "submitted": "Submitted",
                 "working": "Working Paper", "in-preparation": "In Preparation; Not Yet Submitted"}

def intl_from_place(place, config):
    """Yes/No/None by the person's rule. Default rule: outside the US = Yes; unknown place = None (ask).
    US markers count only as the last comma-separated part ("City, ST" / "City, State"); country names and
    well-known non-US cities anywhere in the text mean Yes; anything else is left for the person."""
    raw = str(place or "").strip()
    if not raw or config.get("international_rule", "outside_us") != "outside_us":
        return None
    parts = [x.strip() for x in raw.split(",") if x.strip()]
    last = parts[-1]; last_n = I.norm_text(last)
    if last_n in US_WORDS or last_n in US_STATES or (len(parts) == 2 and last.upper() in US_CODES and last.isupper()):
        return "No"
    if last_n in COUNTRIES:
        return "Yes"
    whole = I.norm_text(raw)
    if any(re.search(r"(?<![a-z])" + re.escape(c) + r"(?![a-z])", whole) for c in COUNTRIES | NON_US_CITIES):
        return "Yes"
    if any(re.search(r"(?<![a-z])" + re.escape(s) + r"(?![a-z])", whole) for s in US_STATES):
        return "No"
    return None

def date_text(it):
    if it["year"] is None:
        return ""
    return f"{MONTH_ABBR[it['month'] - 1]} {it['year']}" if it["month"] else str(it["year"])

def screen_for(kind, screen_kinds, forms):
    for sid, sk in screen_kinds.items():
        if sk["kind"] == kind and sid in forms:
            return sid
    return None

def title_line(it):
    return " · ".join(x for x in [str(it["year"] or ""), it["title"], it["venue"]] if x)

def _value(spec, it, config):
    if "from" in spec:
        v = it.get(spec["from"], "")
        return v if isinstance(v, str) else ""
    if spec.get("people"):
        return ", ".join(it.get("people", []))
    if "const" in spec:
        return spec["const"]
    if "date" in spec:
        if "if_status" in spec and it.get("status", "") not in spec["if_status"]:
            return None
        return date_text(it)
    if spec.get("intl"):
        return intl_from_place(it["place"], config)
    if spec.get("status"):
        return STATUS_OPTION.get(it.get("status", ""))
    return None

def _fit_option(v, options):
    """Return the option matching v (case-insensitive, normalized), else None."""
    if v is None or not options:
        return v
    key = I.norm_text(v)
    for o in options:
        if I.norm_text(o) == key:
            return o
    return None

def propose(matches, works, resume, forms, field_map, screen_kinds, config):
    by_r = {r["id"]: r for r in resume}; by_w = {w["id"]: w for w in works}
    out = []
    for rid in matches["resume_only"]:
        it = by_r[rid]; sid = screen_for(it["kind"], screen_kinds, forms)
        if sid is None:
            continue
        fmap = field_map.get(sid, {}); fields = []
        for f in forms[sid]["fields"]:
            spec = fmap.get(f["name"], {})
            v = _value(spec, it, config) if spec else f.get("default")
            if f["type"] == "combo":
                v = _fit_option(v, f["options"])
            fields.append({"name": f["name"], "prefix": f["prefix"], "type": f["type"], "options": f["options"],
                           "required": f["required"], "value": v, "note": spec.get("note", f.get("note", ""))})
        out.append({"id": rid, "action": "create", "kind": it["kind"], "screen": sid, "screenName": forms[sid]["name"],
                    "resume_id": rid, "title_line": title_line(it), "fields": fields})      # id = resume id, so answers survive a re-run
    for wid in matches["works_only"]:
        w = by_w[wid]
        out.append({"id": wid, "action": "review", "works_id": wid, "kind": w["kind"], "title_line": title_line(w)})
    return out

def main(audit_dir):
    d = pathlib.Path(audit_dir); here = pathlib.Path(__file__).resolve().parent; root = here.parent
    load = lambda p: json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    out = propose(load(d / "matches.json"), I.load_items(d / "works_items.json"), I.load_items(d / "resume_items.json"),
                  load(root / "screens" / "forms.json"), load(here / "field_map.json"), load(here / "screen_kinds.json"),
                  load(root / "local" / "config.json"))
    (d / "proposals.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"create={sum(p['action'] == 'create' for p in out)} review={sum(p['action'] == 'review' for p in out)}")

if __name__ == "__main__":
    main(sys.argv[1])
