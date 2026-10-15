"""Parse raw list-view extracts into records.json and flag incomplete fields into audit.json.

Usage: python3 build_audit.py AUDIT_DIR
  reads  AUDIT_DIR/raw/extract_*.txt   (format documented at the top of those files)
  writes AUDIT_DIR/records.json        {screenId: {name, headers, records: {id: {field: value}}}}
         AUDIT_DIR/audit.json          [{id, screen, screenName, title, year, flags: {...}, current: {...}}]

The five audited fields (see docs/specs/2026-10-13-works-field-audit-design.md) map to Works
columns by the regexes in FIELD_PATTERNS. A screen that lacks a column is not flagged for it.
"""
import json, re, sys, pathlib

FIELD_PATTERNS = {
    "aacsb":    r"^AACSB( Classification)?$",
    "teaching": r"^Related to Teaching and Learning\??$",
    "intl":     r"^Was/is this an international activity\??$",
    "scale":    r"^Scale$",
    "start":    r"^(Start Date|Date Advising Began|Start Date of Funding)$",
    "end":      r"^(End Date|Date Advising Ended|End Date of Funding)$",
}
TITLE_FIELDS = ["Presentation Title", "Title of Contribution", "Title", "Article/Program Title",
                "Name (e.g. committee, organization, etc.)", "Organization/Committee/ Conference/Publication Name",
                "Organization/Committee/Club", "Client/Organization", "Name of Student(s) or Group/Organization",
                "Title of Work", "Degree", "Title/Rank", "Type"]
CONTEXT_FIELDS = ["Conference/Meeting Name", "Position/Role", "Position/Role/Activity", "Role", "Committee Type",
                  "Journal/Publisher/Proceedings Publisher", "Current Status", "Activity Type", "Involvement Type",
                  "Sponsoring Organization", "Institution", "Media Name/Organization", "City", "State", "Country",
                  "Last Name", "First Name", "Mentor Name/Committee (if applicable)", "Organization/Institution/Entity"]
US_STATES = {"Pennsylvania","New Hampshire","Michigan","Minnesota","Massachusetts","Utah","Washington","California",
             "Illinois","IL","WI","Ohio","District of Columbia","CA","MO"}

def parse(raw_dir):
    screens = {}
    cur = None
    for path in sorted(raw_dir.glob("extract_*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.startswith("#"):
                continue
            if line.startswith("SCREEN "):
                sid, _, name = line[7:].partition(" ")
                cur = screens.setdefault(sid, {"name": name.strip(), "headers": [], "records": {}})
            elif line.startswith("H "):
                cur["headers"].append(line[2:].strip())
            elif " ‖ " in line:
                rid, _, rest = line.partition(" ‖ ")
                rec = {}
                for part in rest.split(" ; "):
                    k, _, v = part.partition(": ")
                    k = k.strip().rstrip("?"); v = v.replace("[TRUNCATED]", "").strip()
                    if k and v:
                        rec[k] = v
                rec["_truncated"] = "[TRUNCATED]" in line
                cur["records"][rid.strip()] = rec
    return screens

def field_col(headers, key):
    pat = re.compile(FIELD_PATTERNS[key], re.I)
    for h in headers:
        if pat.match(h.rstrip("?")):
            return h.rstrip("?")
    return None

def year_of(rec):
    for k in ["Year, Date", "Year, Start Date", "Year, End Date", "Year, Date Advising Began", "Year, Date Published",
              "Year, Date Accepted", "Year, Draft Start Date", "Year, Date Proposal Submitted", "Year, Date Completed",
              "Year, Term and Year", "Year Started at Position"]:
        if k in rec:
            return rec[k]
    m = re.search(r"\b(19|20)\d\d\b", rec.get("Record Start Date", "") or rec.get("Record End Date", ""))
    return m.group(0) if m else ""

def suggest_intl(rec):
    if re.search(r"\bvirtual\b|\bonline\b", rec.get("Conference/Meeting Name", ""), re.I):
        return "No"   # no travel; Works' International Engagement Summary asks where activities took place
    c = rec.get("Country", "")
    if c in ("United States", "USA"):
        return "No"
    if c:
        return "Yes"
    if rec.get("State", "") in US_STATES or rec.get("If activity took place outside of Minnesota, indicate which state"):
        return "No"
    if rec.get("Institution", "") == "University of Minnesota":
        return "No"
    return ""

def main(audit_dir):
    audit_dir = pathlib.Path(audit_dir)
    screens = parse(audit_dir / "raw")
    (audit_dir / "records.json").write_text(json.dumps(screens, indent=1, ensure_ascii=False), encoding="utf-8")
    out = []
    for sid, s in screens.items():
        cols = {k: field_col(s["headers"], k) for k in FIELD_PATTERNS}
        for rid, rec in s["records"].items():
            title = next((rec[t] for t in TITLE_FIELDS if rec.get(t)), rid)
            if "Last Name" in rec and "First Name" in rec and title == rid:
                title = f'{rec["First Name"]} {rec["Last Name"]}'
            ctx = [rec[c] for c in CONTEXT_FIELDS if rec.get(c) and rec[c] != title]
            current = {k: (rec.get(c, "") if c else None) for k, c in cols.items()}
            flags = {}
            if cols["aacsb"] and not current["aacsb"]:
                flags["aacsb"] = {"ask": True}
            if cols["intl"] and not current["intl"]:
                flags["intl"] = {"ask": True, "suggest": suggest_intl(rec)}
            if cols["scale"] and not current["scale"]:
                flags["scale"] = {"ask": True}
            if cols["start"] and not current["start"]:
                flags["start"] = {"ask": True, "hint": rec.get("End Date", "") or rec.get("Date Proposal Submitted", "")}
            if cols["end"] and not current["end"]:
                flags["end"] = {"ask": False, "ongoing": True}
            if cols["teaching"]:
                flags["teaching"] = {"ask": False, "toggle": True}
            out.append({"id": rid, "screen": sid, "screenName": s["name"], "title": title, "year": year_of(rec),
                        "context": " · ".join(ctx[:4]), "columns": cols, "current": current, "flags": flags})
    (audit_dir / "audit.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    n_ask = sum(1 for e in out if any(f.get("ask") for f in e["flags"].values()))
    print(f"screens={len(screens)} records={len(out)} records_with_questions={n_ask}")
    for k in FIELD_PATTERNS:
        print(f"  {k}: asked on {sum(1 for e in out if e['flags'].get(k, {}).get('ask'))} records")

if __name__ == "__main__":
    main(sys.argv[1])
