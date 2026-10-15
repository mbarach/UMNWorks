"""Export a Claude Code session (.jsonl) to a readable Markdown transcript.

Usage: python3 export_transcript.py SESSION.jsonl OUT.md [--thinking]
Keeps what a reader needs: your messages, Claude's replies, each tool call (name + short input),
and the first lines of each tool result. Drops system reminders, hidden reasoning (unless
--thinking), and large payloads (screenshots, long outputs are truncated).
"""
import json, re, sys, pathlib

src, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
show_thinking = "--thinking" in sys.argv
MAX_RESULT, MAX_INPUT = 600, 300

def clean(text):
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    text = re.sub(r"<pasted_content[^>]*>", "", text); text = text.replace("</pasted_content>", "")
    return text.strip()

def short(s, n):
    s = str(s).replace("\n", " ⏎ ")
    return s if len(s) <= n else s[:n] + " …"

lines = []
for raw in src.read_text(encoding="utf-8").splitlines():
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        continue
    if d.get("type") not in ("user", "assistant"):
        continue
    m = d.get("message") or {}
    content = m.get("content")
    ts = (d.get("timestamp") or "")[:19].replace("T", " ")
    role = "You" if d["type"] == "user" else "Claude"
    if isinstance(content, str):
        t = clean(content)
        if t:
            lines.append(f"\n## {role}  <small>{ts}</small>\n\n{t}\n")
        continue
    if not isinstance(content, list):
        continue
    header_done = False
    for b in content:
        bt = b.get("type")
        if bt == "text":
            t = clean(b.get("text", ""))
            if not t:
                continue
            if not header_done:
                lines.append(f"\n## {role}  <small>{ts}</small>\n"); header_done = True
            lines.append(t + "\n")
        elif bt == "thinking" and show_thinking:
            lines.append(f"\n> *(thinking)* {short(b.get('thinking',''), 800)}\n")
        elif bt == "tool_use":
            name = b.get("name", "?"); inp = b.get("input", {})
            if isinstance(inp, dict):
                keyed = {k: v for k, v in inp.items() if k not in ("content",)}
                summary = short(json.dumps(keyed, ensure_ascii=False), MAX_INPUT)
            else:
                summary = short(inp, MAX_INPUT)
            lines.append(f"- 🔧 **{name}** `{summary}`")
        elif bt == "tool_result":
            c = b.get("content")
            if isinstance(c, list):
                texts = [x.get("text", "") for x in c if x.get("type") == "text"]
                imgs = sum(1 for x in c if x.get("type") == "image")
                c = "\n".join(texts) + (f" [{imgs} image(s)]" if imgs else "")
            c = clean(str(c or ""))
            if c:
                lines.append(f"  - ↩ {short(c, MAX_RESULT)}")
out.write_text("# Session transcript\n\nSource: `" + src.name + "`\n" + "\n".join(lines) + "\n", encoding="utf-8")
print("wrote", out, out.stat().st_size, "bytes")
