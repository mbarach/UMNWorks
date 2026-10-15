"""One item schema for Works records and resume entries. See docs/item-schema.md.

CLI: python3 -I scripts/items.py FILE   -> validates a JSON list of items; exit 1 on errors.
"""
import json, re, sys, unicodedata

KINDS = ("publication", "presentation", "honor", "service", "grant", "position", "education", "other")
KEYS = {"id": str, "kind": str, "title": str, "venue": str, "year": (int, type(None)), "month": (int, type(None)),
        "people": list, "place": str, "status": str, "source": str, "ref": str, "source_text": str}
STOPWORDS = {"a", "an", "the", "of", "in", "on", "and", "for", "to", "at", "by", "with", "from", "its", "vs"}

def norm_text(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c if ord(c) < 128 else " " for c in s)      # accents were split off by NFKD; other non-ASCII (em dashes) become spaces
    s = re.sub(r"[^a-z0-9]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()

def tokens(s):
    return {t for t in norm_text(s).split() if t not in STOPWORDS}

def validate_items(items):
    errs, seen = [], set()
    if not isinstance(items, list):
        return ["top level must be a JSON list"]
    for n, it in enumerate(items):
        tag = f"item {n} ({it.get('id', '?') if isinstance(it, dict) else '?'})"
        if not isinstance(it, dict):
            errs.append(f"{tag}: not an object"); continue
        for k, typ in KEYS.items():
            if k not in it:
                errs.append(f"{tag}: missing key {k}")
            elif not isinstance(it[k], typ) or (typ is int or isinstance(typ, tuple)) and isinstance(it[k], bool):
                errs.append(f"{tag}: {k} has wrong type")
        if it.get("kind") not in KINDS:
            errs.append(f"{tag}: kind must be one of {', '.join(KINDS)}")
        if it.get("source") not in ("works", "resume"):
            errs.append(f"{tag}: source must be works or resume")
        if it.get("source") == "works" and not re.fullmatch(r"\d{12}", str(it.get("ref", ""))):
            errs.append(f"{tag}: works ref must be the 12-digit record id")
        if isinstance(it.get("people"), list) and not all(isinstance(p, str) for p in it["people"]):
            errs.append(f"{tag}: people must be a list of strings")
        if isinstance(it.get("year"), int) and not 1950 <= it["year"] <= 2100:
            errs.append(f"{tag}: year out of range")
        if isinstance(it.get("month"), int) and not 1 <= it["month"] <= 12:
            errs.append(f"{tag}: month out of range")
        if it.get("id") in seen:
            errs.append(f"{tag}: duplicate id")
        seen.add(it.get("id"))
    return errs

def load_items(path):
    with open(path, encoding="utf-8") as f:
        items = json.load(f)
    errs = validate_items(items)
    if errs:
        raise ValueError("\n".join(errs))
    return items

if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)
    problems = validate_items(data)
    print("\n".join(problems) if problems else f"ok {len(data)} items")
    sys.exit(1 if problems else 0)
