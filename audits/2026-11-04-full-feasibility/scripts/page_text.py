"""Print the visible text of a downloaded HTML page, optionally only the context around keywords (data only)."""
import html
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
h = open(sys.argv[1], encoding="utf-8", errors="replace").read()
h = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", h, flags=re.S | re.I)
t = html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"<(br|p|div|li|h\d|tr)[^>]*>", "\n", h, flags=re.I)))
t = re.sub(r"[ \t\r\f\v]+", " ", t)
t = re.sub(r"\n\s*\n+", "\n", t).strip()
if len(sys.argv) > 2 and sys.argv[2] == "head":
    print(t[: int(sys.argv[3])])
elif len(sys.argv) > 2:
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 220
    for m in re.finditer(sys.argv[2], t, flags=re.I):
        print("...", t[max(0, m.start() - width): m.end() + width].replace("\n", " / "), "...")
else:
    print(t)
