"""Render site/index.html from site/answers.json."""
import json, os, html, datetime, re

ROOT = os.path.join(os.path.dirname(__file__), "..", "site")
data = json.load(open(os.path.join(ROOT, "answers.json")))
tpl = open(os.path.join(os.path.dirname(__file__), "template.html")).read()


def para(text):
    def inline(p):
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html.escape(p.strip()))
    return "".join(f"<p>{inline(p)}</p>" for p in text.split("\n\n") if p.strip())


sections = []
for a in data["answers"]:
    words = len(a["answer"].split())
    size = "s" if words > 90 else "m" if words > 55 else "l"
    origin = "open-weight model by " + a["maker"] if a["open_weights"] else a["maker"]
    sections.append(
        f'<section class="answer size-{size}" id="{a["id"]}">'
        f'<blockquote>{para(a["answer"])}</blockquote>'
        f'<p class="who"><span class="name">{html.escape(a["name"])}</span>'
        f'<span class="maker">{html.escape(origin)}</span></p></section>'
    )

dates = sorted({a["date"] for a in data["answers"]})
d = datetime.date.fromisoformat(dates[-1])
out = (tpl.replace("{{QUESTION}}", html.escape(data["question"]))
          .replace("{{COUNT}}", str(len(sections)))
          .replace("{{DATE}}", f"{d.day} {d:%B %Y}")
          .replace("{{ANSWERS}}", "\n".join(sections)))
open(os.path.join(ROOT, "index.html"), "w").write(out)
print("wrote site/index.html with", len(sections), "answers")
