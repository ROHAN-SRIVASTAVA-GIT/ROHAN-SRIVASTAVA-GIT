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
    stats = {"repos": 36, "stars": 0, "commits": 157, "followers": 1,
             "prs": 2, "issues": 0}
    try:
        user = api_get(f"https://api.github.com/users/{USER}")
        stats["repos"] = user["public_repos"]
        stats["followers"] = user["followers"]
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
        stats["stars"] = stars
    except Exception as e:
        print(f"warn: stars fetch failed: {e}")
    for key, q in (("commits", f"https://api.github.com/search/commits?q=author:{USER}"),
                   ("prs", f"https://api.github.com/search/issues?q=author:{USER}+type:pr"),
                   ("issues", f"https://api.github.com/search/issues?q=author:{USER}+type:issue")):
        try:
            stats[key] = api_get(q)["total_count"]
        except Exception as e:
            print(f"warn: {key} fetch failed: {e}")
    return stats


def fetch_languages():
    """Aggregate language bytes across owned (non-fork) repos."""
    langs = {}
    try:
        page = 1
        while True:
            repos = api_get(f"https://api.github.com/users/{USER}/repos?per_page=100&page={page}")
            for repo in repos:
                if repo["fork"]:
                    continue
                for lang, size in api_get(repo["languages_url"]).items():
                    langs[lang] = langs.get(lang, 0) + size
            if len(repos) < 100:
                break
            page += 1
    except Exception as e:
        print(f"warn: languages fetch failed: {e}")
    return langs


def calculate_rank(stats):
    """Percentile rank, same formula as github-readme-stats calculateRank."""
    def exp_cdf(x):
        return 1 - 2 ** -x

    def log_norm_cdf(x):
        return x / (1 + x)

    score = (2 * exp_cdf(stats["commits"] / 250)
             + 3 * exp_cdf(stats["prs"] / 50)
             + 1 * exp_cdf(stats["issues"] / 25)
             + 1 * exp_cdf(0 / 2)  # reviews
             + 4 * log_norm_cdf(stats["stars"] / 50)
             + 1 * log_norm_cdf(stats["followers"] / 10)) / 12
    percentile = (1 - score) * 100
    for threshold, level in ((1, "S"), (12.5, "A+"), (25, "A"), (37.5, "A-"),
                             (50, "B+"), (62.5, "B"), (75, "B-"), (87.5, "C+"),
                             (100, "C")):
        if percentile <= threshold:
            return percentile, level
    return percentile, "C"


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


# tokyonight-style theme shared by the two stat cards (matches README config)
CARD = {"bg": "#0D1B2E", "title": "#00D4FF", "icon": "#7B2FFF", "text": "#F0F4FF"}

OCTICONS = {
    "star": "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Zm0 2.445L6.615 5.5a.75.75 0 0 1-.564.41l-3.097.45 2.24 2.184a.75.75 0 0 1 .216.664l-.528 3.084 2.769-1.456a.75.75 0 0 1 .698 0l2.77 1.456-.53-3.084a.75.75 0 0 1 .216-.664l2.24-2.183-3.096-.45a.75.75 0 0 1-.564-.41L8 2.694Z",
    "commit": "M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z",
    "pr": "M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z",
    "issue": "M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z M8 0a8 8 0 1 1 0 16A8 8 0 0 1 8 0ZM1.5 8a6.5 6.5 0 1 0 13 0 6.5 6.5 0 0 0-13 0Z",
    "repo": "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8ZM5 12.25a.25.25 0 0 1 .25-.25h3.5a.25.25 0 0 1 .25.25v3.25a.25.25 0 0 1-.4.2l-1.45-1.087a.249.249 0 0 0-.3 0L5.4 15.7a.25.25 0 0 1-.4-.2Z",
}

LANG_COLORS = {
    "Jupyter Notebook": "#DA5B0B", "HTML": "#e34c26", "JavaScript": "#f1e05a",
    "CSS": "#563d7c", "PHP": "#4F5D95", "TypeScript": "#3178c6",
    "Java": "#b07219", "Python": "#3572A5", "C++": "#f34b7d", "C": "#555555",
    "Shell": "#89e051", "Dockerfile": "#384d54", "SCSS": "#c6538c",
    "Kotlin": "#A97BFF", "Go": "#00ADD8", "Vue": "#41b883", "Dart": "#00B4AB",
    "Batchfile": "#C1F12E", "PowerShell": "#012456",
}


def render_stats_card(stats):
    percentile, level = calculate_rank(stats)
    rows = [
        ("star", "Total Stars Earned", stats["stars"]),
        ("commit", "Total Commits", stats["commits"]),
        ("pr", "Total PRs", stats["prs"]),
        ("issue", "Total Issues", stats["issues"]),
        ("repo", "Total Repositories", stats["repos"]),
    ]
    body = []
    y = 60
    for icon, label, value in rows:
        body.append(f'<g transform="translate(25,{y - 12})"><path fill="{CARD["icon"]}" d="{OCTICONS[icon]}"/></g>')
        body.append(f'<text x="50" y="{y}" fill="{CARD["text"]}" font-size="14" font-weight="600">{esc(label)}:</text>')
        body.append(f'<text x="230" y="{y}" fill="{CARD["text"]}" font-size="14" font-weight="600">{value:,}</text>')
        y += 25
    # rank ring
    circumference = 2 * 3.14159 * 40
    fill_frac = max(0.02, (100 - percentile) / 100)
    body.append(f'<circle cx="415" cy="98" r="40" stroke="{CARD["icon"]}" stroke-opacity="0.35" stroke-width="6" fill="none"/>')
    body.append(f'<circle cx="415" cy="98" r="40" stroke="{CARD["title"]}" stroke-width="6" fill="none" stroke-linecap="round" '
                f'stroke-dasharray="{circumference:.1f}" stroke-dashoffset="{circumference * (1 - fill_frac):.1f}" '
                f'transform="rotate(-90 415 98)"/>')
    body.append(f'<text x="415" y="107" fill="{CARD["title"]}" font-size="26" font-weight="800" text-anchor="middle">{level}</text>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" '
           f'font-family="Segoe UI, Ubuntu, sans-serif">'
           f'<rect width="495" height="195" rx="12" fill="{CARD["bg"]}"/>'
           f'<text x="25" y="33" fill="{CARD["title"]}" font-size="18" font-weight="700">Rohan Srivastava\'s GitHub Stats</text>'
           + "".join(body) + '</svg>')
    with open("stats_card.svg", "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print("wrote stats_card.svg")


def render_top_langs(langs, count=8):
    total = sum(langs.values())
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:count] if total else []
    body = []
    # stacked bar
    bar_x, bar_w, bar_y = 25, 300, 47
    body.append(f'<mask id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="8" rx="4" fill="white"/></mask>')
    x = float(bar_x)
    for lang, size in top:
        w = size / total * bar_w
        color = LANG_COLORS.get(lang, "#858585")
        body.append(f'<rect mask="url(#bar)" x="{x:.2f}" y="{bar_y}" width="{w + 1:.2f}" height="8" fill="{color}"/>')
        x += w
    # legend, two columns
    for i, (lang, size) in enumerate(top):
        col, row = i % 2, i // 2
        lx = 25 + col * 165
        ly = 80 + row * 22
        color = LANG_COLORS.get(lang, "#858585")
        pct = size / total * 100
        name = lang if len(lang) <= 16 else lang[:15] + "…"
        body.append(f'<circle cx="{lx + 5}" cy="{ly - 4}" r="5" fill="{color}"/>')
        body.append(f'<text x="{lx + 18}" y="{ly}" fill="{CARD["text"]}" font-size="12" font-weight="600">{esc(name)} {pct:.2f}%</text>')
    rows = (len(top) + 1) // 2
    height = 80 + rows * 22
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="350" height="{height}" viewBox="0 0 350 {height}" '
           f'font-family="Segoe UI, Ubuntu, sans-serif">'
           f'<rect width="350" height="{height}" rx="12" fill="{CARD["bg"]}"/>'
           f'<text x="25" y="33" fill="{CARD["title"]}" font-size="18" font-weight="700">Most Used Languages</text>'
           + "".join(body) + '</svg>')
    with open("top_langs.svg", "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    print("wrote top_langs.svg")


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
    info.append(twostat(470, "Repos", f"{stats['repos']:,}", "Stars", f"{stats['stars']:,}"))
    info.append(twostat(490, "Commits", f"{stats['commits']:,}", "Followers", f"{stats['followers']:,}"))
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

    render_stats_card(stats)
    langs = fetch_languages()
    if langs:
        render_top_langs(langs)
    else:
        print("skip: top_langs.svg kept from previous run (no language data)")


if __name__ == "__main__":
    main()
