#!/usr/bin/env python3
"""Build the theme-stock-brief pages and the weekly email from the JSON data files.

Usage:
  python3 build.py kr|us|all          # validate data, write out/<market>.html
  python3 build.py all --email        # also write out/email.html and out/email.txt
  python3 build.py all --snapshot     # also copy data/<market>.json to data/history/<asOf-date>-<market>.json
  python3 build.py check              # validate only

Paths are resolved relative to the plugin root (the parent of this scripts/ folder).
"""
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "out"
TEMPLATE = ROOT / "assets" / "template.html"
CONFIG = DATA / "config.json"
MARKETS = ("kr", "us")
TAGS = {"up", "down", "mid"}
PHASES = {"real", "order", "hope", "policy"}


def load(market):
    return json.loads((DATA / f"{market}.json").read_text(encoding="utf-8"))


def config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def validate(market, d):
    """Return a list of problems; empty means the data is consistent."""
    errs = []
    src = d.get("sources", {})

    def need_src(keys, where):
        for k in keys or []:
            if k not in src:
                errs.append(f"{where}: unknown source key '{k}'")

    for key in ("meta", "tiles", "themes", "macro", "heatmap", "regime", "calendar", "sources", "disclaimer"):
        if key not in d:
            errs.append(f"missing top-level key '{key}'")
    if errs:
        return errs
    theme_ids = {t["id"]: t for t in d["themes"]}
    for t in d["themes"]:
        for si, s in enumerate(t["stages"]):
            where = f"themes.{t['id']}.stages[{si}] {s.get('n')}"
            if s.get("ph") not in PHASES:
                errs.append(f"{where}: bad phase {s.get('ph')}")
            if not s.get("co"):
                errs.append(f"{where}: no companies")
            for c in s.get("co", []):
                need_src(c.get("s"), f"{where} / {c.get('n')}")
            for n in s.get("news", []):
                if n[0] not in TAGS:
                    errs.append(f"{where}: bad news tag {n[0]}")
            for c in s.get("cases", []):
                need_src(c.get("s"), f"{where} case {c.get('d')}")
                if c.get("g") and c["g"] not in TAGS:
                    errs.append(f"{where}: bad case tag {c['g']}")
            for l in s.get("links", []):
                if "url" in l:
                    continue
                tt = theme_ids.get(l.get("th"))
                if not tt or not (0 <= l.get("i", -1) < len(tt["stages"])):
                    errs.append(f"{where}: link points nowhere {l}")
    m = d["macro"]
    nmonths = len(m["months"])
    gkeys = [g["k"] for g in m["groups"]]
    ind_ids = set()
    for ind in m["inds"]:
        where = f"macro.{ind.get('id')}"
        ind_ids.add(ind["id"])
        if ind.get("series") is not None and len(ind["series"]) != nmonths:
            errs.append(f"{where}: series has {len(ind['series'])} points, months has {nmonths}")
        if not (ind.get("series") or ind.get("stats") or ind.get("bars")):
            errs.append(f"{where}: needs series, stats or bars")
        for g in gkeys:
            cell = ind["cells"].get(g)
            if not cell or not isinstance(cell[0], int) or not -3 <= cell[0] <= 3:
                errs.append(f"{where}: bad cell for group {g}")
        for c in ind.get("cases", []):
            need_src(c.get("s"), f"{where} case {c.get('d')}")
    for ev in m.get("events", []):
        if not 0 <= ev["i"] < nmonths:
            errs.append(f"macro event out of range {ev}")
    ncols = len(d["heatmap"]["cols"])
    for b in d["heatmap"]["bands"]:
        for r in b["rows"]:
            where = f"heatmap.{b['band']}.{r['n']}"
            if len(r["v"]) != ncols:
                errs.append(f"{where}: {len(r['v'])} values for {ncols} columns")
            if any(v not in (-2, -1, 0, 1, 2) for v in r["v"]):
                errs.append(f"{where}: values must be -2..2")
            if r.get("ref") and r["ref"] not in ind_ids:
                errs.append(f"{where}: ref {r['ref']} is not a macro indicator")
            if not r.get("ref") and not r.get("path"):
                errs.append(f"{where}: needs a path (or a ref to a macro indicator)")
            for c in r.get("cases", []):
                need_src(c.get("s"), f"{where} case {c.get('d')}")
    for r in d["regime"]:
        if r["tag"] not in TAGS:
            errs.append(f"regime {r['h']}: bad tag")
    return errs


def fill_links(obj, cfg):
    """Replace __KR_URL__ / __US_URL__ placeholders with the published artifact URLs."""
    text = json.dumps(obj, ensure_ascii=False)
    for m in MARKETS:
        url = cfg["artifacts"].get(m) or "#"
        text = text.replace(f"__{m.upper()}_URL__", url)
    return json.loads(text)


def build_page(market, cfg):
    d = fill_links(load(market), cfg)
    payload = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("__TITLE__", html.escape(d["meta"]["title"])).replace("/*__DATA__*/", payload)
    OUT.mkdir(exist_ok=True)
    path = OUT / f"{market}.html"
    path.write_text(page, encoding="utf-8")
    return path


def macro_scores(d):
    m = d["macro"]
    return [(g["n"], sum(ind["cells"][g["k"]][0] for ind in m["inds"])) for g in m["groups"]]


def movers(d, n=5):
    """Top and bottom weekly movers among companies that carry Zacks metrics (k.w1)."""
    seen, rows = set(), []
    for t in d["themes"]:
        for s in t["stages"]:
            for c in s["co"]:
                k = c.get("k") or {}
                if k.get("w1") is None or c.get("c") in seen:
                    continue
                seen.add(c.get("c"))
                rows.append((c["n"], c.get("c", ""), k["w1"], k.get("ytd")))
    rows.sort(key=lambda r: r[2], reverse=True)
    return rows[:n], rows[-n:][::-1]


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def fmt_pct(v):
    if v is None:
        return "–"
    sign = "+" if v > 0 else "−" if v < 0 else ""
    return f"{sign}{abs(v):.1f}%"


def build_email(cfg):
    kr, us = fill_links(load("kr"), cfg), fill_links(load("us"), cfg)
    today = date.today().isoformat()
    ink, mute, line, up, down = "#11161d", "#5a616c", "#e2e5ea", "#1c5cab", "#b02a2a"
    tag_style = {"up": f"background:#e3eefb;color:{up}", "down": f"background:#fbe4e3;color:{down}", "mid": f"background:#eceef1;color:{mute}"}
    tag_txt = {"up": "상승기여", "down": "하락원인으로예상", "mid": "중립·관망"}

    def tag(t):
        return f'<span style="{tag_style[t]};font-size:12px;font-weight:600;padding:2px 6px;border-radius:4px;white-space:nowrap">{tag_txt[t]}</span>'

    def tiles(d):
        cells = "".join(
            f'<td style="padding:8px 10px;border:1px solid {line};vertical-align:top;width:33%">'
            f'<div style="font-size:12px;color:{mute}">{html.escape(t["label"])}</div>'
            f'<div style="font-size:18px;font-weight:700;color:{up if t.get("dir") == "up" else down if t.get("dir") == "down" else ink}">{html.escape(t["value"])}</div>'
            f'<div style="font-size:11px;color:{mute}">{html.escape(t["note"])}</div></td>'
            + ("</tr><tr>" if i == 2 else "")
            for i, t in enumerate(d["tiles"][:6]))
        return f'<table role="presentation" cellspacing="0" cellpadding="0" style="border-collapse:collapse;width:100%"><tr>{cells}</tr></table>'

    def scores(d):
        out = []
        for name, s in macro_scores(d):
            t = "up" if s > 0 else "down" if s < 0 else "mid"
            out.append(f'<tr><td style="padding:4px 0;font-size:13px">{html.escape(name)}</td><td style="padding:4px 0;font-size:13px;font-weight:700;text-align:right">{"+" if s > 0 else ""}{s}</td><td style="padding:4px 0 4px 10px">{tag(t)}</td></tr>')
        return f'<table role="presentation" style="border-collapse:collapse;width:100%">{"".join(out)}</table>'

    def regime(d):
        return "".join(f'<p style="margin:0 0 8px;font-size:13px;line-height:1.6">{tag(r["tag"])} <b>{html.escape(r["h"])}</b> — {html.escape(r["p"])}</p>' for r in d["regime"])

    def mover_table(d):
        top, bottom = movers(d)
        def rows(rs):
            return "".join(f'<tr><td style="padding:3px 0;font-size:13px">{html.escape(n)} <span style="color:{mute}">{html.escape(c)}</span></td><td style="padding:3px 0;font-size:13px;text-align:right;color:{up if w > 0 else down}">{fmt_pct(w)}</td></tr>' for n, c, w, _ in rs)
        return (f'<table role="presentation" style="width:100%;border-collapse:collapse"><tr><td style="vertical-align:top;width:50%;padding-right:10px">'
                f'<div style="font-size:12px;color:{mute};margin-bottom:4px">주간 상승 상위</div><table style="width:100%;border-collapse:collapse">{rows(top)}</table></td>'
                f'<td style="vertical-align:top;width:50%;padding-left:10px"><div style="font-size:12px;color:{mute};margin-bottom:4px">주간 하락 상위</div><table style="width:100%;border-collapse:collapse">{rows(bottom)}</table></td></tr></table>')

    def section(title, d, link, with_movers):
        return (f'<h2 style="font-size:17px;margin:28px 0 8px;color:{ink}">{html.escape(title)}</h2>'
                f'<p style="margin:0 0 10px;font-size:14px;line-height:1.6;color:{ink}">{html.escape(strip_tags(d["meta"]["lead"]))}</p>'
                f'{tiles(d)}'
                f'<h3 style="font-size:14px;margin:16px 0 6px">거시 순풍·역풍 점수</h3>{scores(d)}'
                f'<h3 style="font-size:14px;margin:16px 0 6px">국면 진단</h3>{regime(d)}'
                + (f'<h3 style="font-size:14px;margin:16px 0 6px">이번 주 움직임 (최근 1주)</h3>{mover_table(d)}' if with_movers else "")
                + f'<p style="margin:12px 0 0"><a href="{html.escape(link)}" style="color:#0f5c55;font-weight:600">도구에서 자세히 보기 →</a></p>')

    def cal_list(items):
        return "".join(f'<li style="margin:0 0 4px;font-size:13px"><b>{html.escape(c["d"])}</b> {html.escape(c["w"])}</li>' for c in items)
    cal = (f'<p style="font-size:12px;color:{mute};margin:0 0 4px">미국</p><ul style="padding-left:18px;margin:0 0 10px">{cal_list(us["calendar"])}</ul>'
           f'<p style="font-size:12px;color:{mute};margin:0 0 4px">한국 관점</p><ul style="padding-left:18px;margin:0">{cal_list(kr["calendar"])}</ul>')
    body = (f'<div style="max-width:640px;margin:0 auto;font-family:-apple-system,\'Apple SD Gothic Neo\',\'Malgun Gothic\',sans-serif;color:{ink}">'
            f'<p style="font-size:12px;color:{mute};margin:0">주간 테마 브리핑 · {today}</p>'
            f'<h1 style="font-size:22px;margin:4px 0 12px">AI·양자·로봇 주간 브리핑</h1>'
            f'<p style="font-size:13px;color:{mute};margin:0">미국 데이터 기준 {html.escape(us["meta"]["asOf"])} · 한국 {html.escape(kr["meta"]["asOf"])}</p>'
            + section("미국", us, cfg["artifacts"].get("us", "#"), True)
            + section("한국", kr, cfg["artifacts"].get("kr", "#"), False)
            + f'<h2 style="font-size:17px;margin:28px 0 8px">다가오는 일정</h2>{cal}'
            f'<p style="font-size:12px;color:{mute};margin:24px 0 0;border-top:1px solid {line};padding-top:10px">도구 링크는 비공개 아티팩트입니다. 받는 분이 열려면 아티팩트 공유 메뉴에서 공유해 주세요. {html.escape(us["disclaimer"])}</p>'
            '</div>')
    OUT.mkdir(exist_ok=True)
    (OUT / "email.html").write_text(body, encoding="utf-8")

    # plain-text alternative
    lines = [f"AI·양자·로봇 주간 브리핑 ({today})", ""]
    for title, d, key in (("미국", us, "us"), ("한국", kr, "kr")):
        lines += [f"[{title}] {strip_tags(d['meta']['lead'])}"]
        lines += [f"- {t['label']}: {t['value']} ({t['note']})" for t in d["tiles"]]
        lines += ["거시 순풍·역풍: " + ", ".join(f"{n} {s:+d}" for n, s in macro_scores(d))]
        lines += [f"- {tag_txt[r['tag']]} {r['h']}: {r['p']}" for r in d["regime"]]
        lines += [f"도구: {cfg['artifacts'].get(key, '')}", ""]
    lines += ["일정 (미국)"] + [f"- {c['d']} {c['w']}" for c in us["calendar"]]
    lines += ["일정 (한국 관점)"] + [f"- {c['d']} {c['w']}" for c in kr["calendar"]]
    lines += ["", us["disclaimer"]]
    (OUT / "email.txt").write_text("\n".join(lines), encoding="utf-8")
    return OUT / "email.html"


def snapshot(market, d):
    tag = re.sub(r"[^0-9-]", "", d["meta"].get("updated", date.today().isoformat()))[:10] or date.today().isoformat()
    dest = DATA / "history" / f"{tag}-{market}.json"
    dest.parent.mkdir(exist_ok=True)
    shutil.copyfile(DATA / f"{market}.json", dest)
    return dest


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    target, flags = argv[0], set(argv[1:])
    markets = MARKETS if target in ("all", "check") else (target,)
    cfg = config()
    bad = False
    for m in markets:
        errs = validate(m, load(m))
        for e in errs:
            print(f"[{m}] {e}")
        bad |= bool(errs)
        print(f"[{m}] {'FAILED' if errs else 'ok'} validation")
    if bad:
        return 1
    if target == "check":
        return 0
    for m in markets:
        print(f"[{m}] wrote {build_page(m, cfg)}")
        if "--snapshot" in flags:
            print(f"[{m}] snapshot {snapshot(m, load(m))}")
    if "--email" in flags:
        print(f"[email] wrote {build_email(cfg)} and email.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
