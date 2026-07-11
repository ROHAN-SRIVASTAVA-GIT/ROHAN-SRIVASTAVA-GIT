#!/usr/bin/env python3
"""Regenerates light_mode.svg and dark_mode.svg for the profile README.

Recomputes uptime (from DOB) and fetches live GitHub stats, then rebuilds
both SVGs around the embedded ASCII portrait. Run daily via GitHub Actions.
"""
import html
import json
import os
import urllib.request
from calendar import monthrange
from datetime import date

USER = "ROHAN-SRIVASTAVA-GIT"
DOB = date(2000, 12, 25)
WIDTH = 60  # chars per info line

ASCII_ART = """\

        ';!lTg%&&%gF!;.
      |gM@@@@@@@@@@@@@Ml`
    ,&@@@@@@@@@@@@@@@@@@@l
    F@$%FTi|:|::!lTTF&$$$@T
  ;M$$i'.          '`|F$@$%
  |@@&`.           .`;|TM@|
   &M!'``..        ',:!!i%
   !g.`:|:|ii;    ,TFTFgi'
   ,T`.'`;l!|;' .,;!lliT|...
  '';'.`;;!;:,`  ;i|!!!l|;
    `.           `;,''`,;;
   .:.           ';;' .,:`
   .l,       ';;;TT:,'`;::
    !g`.  ;Tlli!:ig&M&l|ll
    !@%!,'||,,`..`|iiiiF$`
   !@$MMF|;'   ,li;,:i%%,
 `l@$$%F%MM%i|::i!T%&$$,
&$@$@@@MT!TM@@@@@@@@M&$$&T!;.
@@$@@@$@@&l:|lFFg%%gg$@@@@@@$%T:`
$$@@@@@$$@@MT|::!lFgM@$$$$$$@@@@$&T:'
@@@@@@@@@$$@@MgTilF&$$@@@@@@$$$$@@@@$F
@@@@@@@@@@@$$@@@MFlFM@$@@@@@@@@@$$$$@@
@@@@@@@@@@@@@$$$@%iF$$@@@@@@@@@@@@@@$$
@@@@@@@@@@@@@@@@$@@@@@@@@@@@@@@@@@@@@@"""


def api_get(url):
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_stats():
    stats = {"repos": "36", "stars": "0", "commits": "157", "followers": "1"}
    try:
        user = api_get(f"https://api.github.com/users/{USER}")
        stats["repos"] = f"{user['public_repos']:,}"
        stats["followers"] = f"{user['followers']:,}"
    except Exception as e:
        print(f"warn: user fetch failed: {e}")
    try:
        stars, page = 0, 1
        while True:
            repos = api_get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}")
            stars += sum(r["stargazers_count"] for r in repos)
            if len(repos) < 100:
                break
            page += 1
        stats["stars"] = f"{stars:,}"
    except Exception as e:
        print(f"warn: stars fetch failed: {e}")
    try:
        found = api_get(f"https://api.github.com/search/commits?q=author:{USER}")
        stats["commits"] = f"{found['total_count']:,}"
    except Exception as e:
        print(f"warn: commits fetch failed: {e}")
    return stats


def uptime_string():
    today = date.today()
    years = today.year - DOB.year
    months = today.month - DOB.month
    days = today.day - DOB.day
    if days < 0:
        months -= 1
        prev_month = today.month - 1 or 12
        prev_year = today.year if today.month > 1 else today.year - 1
        days += monthrange(prev_year, prev_month)[1]
    if months < 0:
        years -= 1
        months += 12
    return f"{years} years, {months} months, {days} days"


def esc(s):
    return html.escape(s, quote=False)


def kv(y, keys, value):
    prefix_len = 2 + sum(len(k) for k in keys) + (len(keys) - 1) + 1
    ndots = max(1, WIDTH - prefix_len - 2 - len(value))
    keyspans = '.'.join(f'<tspan class="key">{esc(k)}</tspan>' for k in keys)
    return (f'<tspan x="390" y="{y}" class="cc">. </tspan>{keyspans}:'
            f'<tspan class="cc"> {"." * ndots} </tspan>'
            f'<tspan class="value">{esc(value)}</tspan>')


def blank(y):
    return f'<tspan x="390" y="{y}" class="cc">. </tspan>'


def header(y, text):
    ndash = WIDTH - len(text) - 5
    return f'<tspan x="390" y="{y}">{esc(text)}</tspan> -{"—" * ndash}-—-'


def twostat(y, k1, v1, k2, v2):
    fixed = 2 + len(k1) + 3 + len(v1) + 3 + len(k2) + 3 + len(v2)
    total_dots = max(2, WIDTH - fixed)
    d1 = total_dots // 2
    d2 = total_dots - d1
    return (f'<tspan x="390" y="{y}" class="cc">. </tspan>'
            f'<tspan class="key">{esc(k1)}</tspan>:<tspan class="cc"> {"." * d1} </tspan>'
            f'<tspan class="value">{esc(v1)}</tspan> | '
            f'<tspan class="key">{esc(k2)}</tspan>:<tspan class="cc"> {"." * d2} </tspan>'
            f'<tspan class="value">{esc(v2)}</tspan>')


INSTA = ('<g stroke="#E4405F" fill="none" stroke-width="1.8">'
         '<rect x="391" y="16.5" width="14.5" height="14.5" rx="4.2"/>'
         '<circle cx="398.2" cy="23.7" r="3.4"/>'
         '<circle cx="402.4" cy="19.5" r="1" fill="#E4405F" stroke="none"/>'
         '</g>')

THEMES = {
    "light_mode.svg": {
        "key": "#953800", "value": "#0a3069", "add": "#1a7f37", "del": "#cf222e",
        "cc": "#c2cfde", "bg": "#f6f8fa", "fg": "#24292f",
    },
    "dark_mode.svg": {
        "key": "#ffa657", "value": "#a5d6ff", "add": "#3fb950", "del": "#f85149",
        "cc": "#616e7f", "bg": "#161b22", "fg": "#c9d1d9",
    },
}


def main():
    stats = fetch_stats()
    handle = "code.withrohan"

    info = []
    info.append(f'<tspan x="413" y="30">{esc(handle)}</tspan> -{"—" * (WIDTH - len(handle) - 8)}-—-')
    info.append(kv(50, ["OS"], "Enterprise Engineer"))
    info.append(kv(70, ["Uptime"], uptime_string()))
    info.append(kv(90, ["Role"], "Software Engineer @ Deloitte (SDA)"))
    info.append(kv(110, ["Company"], "Centroxy Solutions Pvt Ltd"))
    info.append(kv(130, ["Education"], "B.Tech CSE - XIM University (2024)"))
    info.append(kv(150, ["IDE"], "IntelliJ IDEA, VS Code"))
    info.append(blank(170))
    info.append(kv(190, ["Languages", "Programming"], "Java, JS, TS, Python, C++"))
    info.append(kv(210, ["Languages", "Web"], "HTML, CSS, JSON, YAML"))
    info.append(kv(230, ["Languages", "Real"], "English, Hindi"))
    info.append(blank(250))
    info.append(kv(270, ["Frameworks"], "Spring Boot, React, Angular, FastAPI"))
    info.append(kv(290, ["Cloud", "DevOps"], "AWS, OpenShift, Docker, Jenkins"))
    info.append(kv(310, ["Certified"], "Oracle Java SE 17 Developer (1Z0-829)"))
    info.append(header(330, "- Contact"))
    info.append(kv(350, ["Email", "Personal"], "srivastavarohan3125@gmail.com"))
    info.append(kv(370, ["LinkedIn"], "https://www.linkedin.com/in/rohan3125/"))
    info.append(kv(390, ["Portfolio"], "rohan-srivastava-git.vercel.app"))
    info.append(kv(410, ["GitHub"], "ROHAN-SRIVASTAVA-GIT"))
    info.append(blank(430))
    info.append(header(450, "- GitHub Stats"))
    info.append(twostat(470, "Repos", stats["repos"], "Stars", stats["stars"]))
    info.append(twostat(490, "Commits", stats["commits"], "Followers", stats["followers"]))
    info.append(kv(510, ["Experience"], "2+ Yrs | 5 Enterprise Projects | 3 Countries"))

    ascii_lines = ASCII_ART.splitlines()
    while len(ascii_lines) < 25:
        ascii_lines.append("")

    for fname, c in THEMES.items():
        parts = []
        parts.append("<?xml version='1.0' encoding='UTF-8'?>")
        parts.append('<svg xmlns="http://www.w3.org/2000/svg" font-family="ConsolasFallback,Consolas,monospace" width="985px" height="530px" font-size="16px">')
        parts.append(f"""<style>
@font-face {{
src: local('Consolas'), local('Consolas Bold');
font-family: 'ConsolasFallback';
font-display: swap;
-webkit-size-adjust: 109%;
size-adjust: 109%;
}}
.key {{fill: {c['key']};}}
.value {{fill: {c['value']};}}
.addColor {{fill: {c['add']};}}
.delColor {{fill: {c['del']};}}
.cc {{fill: {c['cc']};}}
text, tspan {{white-space: pre;}}
</style>""")
        parts.append(f'<rect width="985px" height="530px" fill="{c["bg"]}" rx="15"/>')
        parts.append(f'<text x="15" y="30" fill="{c["fg"]}" class="ascii">')
        for i, line in enumerate(ascii_lines):
            parts.append(f'<tspan x="15" y="{30 + i * 20}">{esc(line)}</tspan>')
        parts.append('</text>')
        parts.append(f'<text x="390" y="30" fill="{c["fg"]}">')
        parts.extend(info)
        parts.append('</text>')
        parts.append(INSTA)
        parts.append('</svg>')
        with open(fname, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n".join(parts))
        print(f"wrote {fname}")


if __name__ == "__main__":
    main()
