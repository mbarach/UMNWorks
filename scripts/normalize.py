"""Turn Works extracts (records.json + audit.json) into items (docs/item-schema.md).

CLI: python3 -I scripts/normalize.py AUDIT_DIR -> AUDIT_DIR/works_items.json, normalize_warnings.json
"""
import json, pathlib, re, sys
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]

def _year(rec, fields):
    for f in fields:
        v = rec.get(f, "")
        if v and v.isdigit():
            return int(v)
    return None

def _month(rec, field):
    v = (rec.get(field, "") if field else "").strip().lower()
    return MONTHS.index(v) + 1 if v in MONTHS else None

def _place(rec):
    return ", ".join(rec[k] for k in ("City", "State", "Country") if rec.get(k))

def works_items(records, audit, screen_kinds):
    out, warnings, seen_unknown = [], [], set()
    for a in audit:
        sid, rid = a["screen"], a["id"]
        rec = records.get(sid, {}).get("records", {}).get(rid, {})
        sk = screen_kinds.get(sid)
        if sk is None:
            if sid not in seen_unknown:
                warnings.append(f"screen {sid} ({a.get('screenName', '?')}) is not in screen_kinds.json; its records are kind other")
                seen_unknown.add(sid)
            sk = {"kind": "other", "venue_field": "", "year_fields": []}
        year = _year(rec, sk.get("year_fields", []))
        if year is None and str(a.get("year", "")).isdigit():
            year = int(a["year"])
        people = [v for k, v in rec.items() if k.startswith("Last Name") and v]
        title = a.get("title", "") if a.get("title") != rid else ""
        if sk.get("role_field") and rec.get(sk["role_field"]):
            title = rec[sk["role_field"]]                 # service: the role is the title, the organization the venue
        out.append({"id": "w" + rid, "kind": sk["kind"], "title": title,
                    "venue": rec.get(sk.get("venue_field", ""), ""), "year": year, "month": _month(rec, sk.get("month_field")),
                    "people": people, "place": _place(rec), "status": rec.get(sk.get("status_field", ""), "").strip().lower(),
                    "source": "works", "ref": rid, "source_text": a.get("context", "")})
    return out, warnings

def screen_diff_warnings(seen, catalog):
    """seen: [{id, name}] from the Activities menu; catalog: {id: name}. Reports both directions."""
    seen_ids = {str(s["id"]): s.get("name", "") for s in seen}
    out = [f"Works shows screen {sid} ({name}) that the catalog does not know" for sid, name in seen_ids.items() if sid not in catalog]
    out += [f"catalog screen {sid} ({name}) was not seen in Works" for sid, name in catalog.items() if sid not in seen_ids]
    return out

def catalog_screens(screen_kinds, screens_md_text):
    cat = {sid: sk.get("note", sk["kind"]) for sid, sk in screen_kinds.items()}
    for m in re.finditer(r"^\| (\d{6,7}) \| ([^|]+) \|", screens_md_text, re.M):
        cat.setdefault(m.group(1), m.group(2).strip())
    return cat

def main(audit_dir):
    d = pathlib.Path(audit_dir)
    records = json.loads((d / "records.json").read_text(encoding="utf-8"))
    audit = json.loads((d / "audit.json").read_text(encoding="utf-8"))
    kinds = json.loads((pathlib.Path(__file__).with_name("screen_kinds.json")).read_text(encoding="utf-8"))
    out, warnings = works_items(records, audit, kinds)
    seen_path = d / "screens_seen.json"
    if seen_path.exists():
        md = pathlib.Path(__file__).resolve().parent.parent / "screens.md"
        warnings += screen_diff_warnings(json.loads(seen_path.read_text(encoding="utf-8")), catalog_screens(kinds, md.read_text(encoding="utf-8") if md.exists() else ""))
    else:
        warnings.append("screens_seen.json missing: the Activities menu was not compared with the catalog")
    (d / "works_items.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    (d / "normalize_warnings.json").write_text(json.dumps(warnings, indent=1), encoding="utf-8")
    print(f"items={len(out)} warnings={len(warnings)}")
    for w in warnings:
        print("  ", w)

if __name__ == "__main__":
    main(sys.argv[1])
