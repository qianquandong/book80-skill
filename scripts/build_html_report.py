#!/usr/bin/env python3
"""Build a self-contained interactive HTML briefing from Markdown and UTF-8 text."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


UI = {
    "zh": {
        "suffix": "交互式速读",
        "subtitle": "摘要与原文对照阅读",
        "toc": "报告目录",
        "choose": "选择报告章节",
        "source": "查看原文",
        "source_help": "点击报告中的引用，直接打开原文并定位。",
        "open": "打开原文阅读器",
        "search": "搜索原文",
        "next": "查找下一处",
        "close": "关闭原文",
        "line": "原文第 {n} 行",
        "lines": "原文共 {n} 行",
        "found": "找到“{q}”：第 {n} 行",
        "missing": "没有找到“{q}”",
        "theme": "切换明暗模式",
    },
    "en": {
        "suffix": "Interactive Brief",
        "subtitle": "Briefing with source text",
        "toc": "Contents",
        "choose": "Choose a section",
        "source": "View source",
        "source_help": "Select a citation to open the source at the matching line.",
        "open": "Open source reader",
        "search": "Search source",
        "next": "Find next",
        "close": "Close source",
        "line": "Source line {n}",
        "lines": "{n} source lines",
        "found": "Found “{q}” at line {n}",
        "missing": "No result for “{q}”",
        "theme": "Toggle theme",
    },
}


def inline(text: str) -> str:
    value = html.escape(text)
    value = re.sub(
        r"\[([^]]+)]\([^)]*#L(\d+)\)",
        lambda m: (
            f'<a class="source-link" href="#source-L{m.group(2)}" '
            f'data-line="{m.group(2)}">{m.group(1)} <span aria-hidden="true">↗</span></a>'
        ),
        value,
    )

    def remaining_link(match: re.Match[str]) -> str:
        label, target = match.groups()
        path = target.split("#", 1)[0].lower()
        if target.startswith(("./", "../")) and path.endswith((".txt", ".html", ".htm")):
            return f'<a class="source-link" href="#source-L1" data-line="1">{label} <span aria-hidden="true">↗</span></a>'
        return f'<a href="{target}">{label}</a>'

    value = re.sub(r"\[([^]]+)]\(([^)]+)\)", remaining_link, value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    return value


def slug(text: str, number: int) -> str:
    clean = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", text).strip("-")
    return clean or f"section-{number}"


def markdown_to_html(markdown: str) -> tuple[str, list[tuple[str, str]]]:
    lines, out, toc = markdown.splitlines(), [], []
    i = section_no = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                code.append(lines[i]); i += 1
            i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(code))}</code></pre>")
            continue
        heading = re.match(r"^(#{1,3})\s+(.+)$", line)
        if heading:
            level, title = len(heading.group(1)), heading.group(2)
            section_no += 1
            anchor = slug(title, section_no)
            out.append(f'<h{level} id="{anchor}">{inline(title)}</h{level}>')
            if level == 2:
                toc.append((anchor, re.sub(r"[*`]", "", title)))
            i += 1
            continue
        if line.startswith("> "):
            quote = []
            while i < len(lines) and lines[i].startswith("> "):
                quote.append(lines[i][2:]); i += 1
            out.append(f'<aside class="note">{"<br>".join(inline(x) for x in quote)}</aside>')
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:|-]+\|$", lines[i + 1]):
            header = [x.strip() for x in line.strip("|").split("|")]
            rows = []
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([x.strip() for x in lines[i].strip("|").split("|")]); i += 1
            head = "".join(f"<th>{inline(x)}</th>" for x in header)
            body = "".join("<tr>" + "".join(f"<td>{inline(x)}</td>" for x in row) + "</tr>" for row in rows)
            out.append(f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')
            continue
        item = re.match(r"^\s*(-|\d+\.)\s+(.+)$", line)
        if item:
            ordered = item.group(1)[0].isdigit()
            tag, items = ("ol" if ordered else "ul"), []
            while i < len(lines):
                match = re.match(r"^\s*(-|\d+\.)\s+(.+)$", lines[i])
                if not match or match.group(1)[0].isdigit() != ordered:
                    break
                items.append(match.group(2)); i += 1
            out.append(f'<{tag}>' + "".join(f"<li>{inline(x)}</li>" for x in items) + f'</{tag}>')
            continue
        paragraph = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"^(#{1,3})\s+|^> |^```|^\||^\s*(-|\d+\.)\s+", lines[i]):
            paragraph.append(lines[i]); i += 1
        out.append(f'<p>{inline(" ".join(paragraph))}</p>')
    return "\n".join(out), toc


CSS = r''':root{color-scheme:light dark;--bg:#f3f4f1;--paper:#fcfcfa;--ink:#20231f;--muted:#646a63;--line:#dfe2dc;--accent:#a33c32;--soft:#f2dfdc;--hit:#ffd970;--shadow:0 20px 65px #262b2522} [data-theme=dark]{--bg:#171916;--paper:#20231f;--ink:#ecede9;--muted:#a8aea5;--line:#383d36;--accent:#e27a6f;--soft:#482e2b;--hit:#6c551c;--shadow:0 20px 65px #0006}@media(prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#171916;--paper:#20231f;--ink:#ecede9;--muted:#a8aea5;--line:#383d36;--accent:#e27a6f;--soft:#482e2b;--hit:#6c551c;--shadow:0 20px 65px #0006}}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:82px}body{margin:0;background:var(--bg);color:var(--ink);font-family:"SF Pro Text","PingFang SC",system-ui,sans-serif;line-height:1.78}.top{position:sticky;top:0;z-index:20;height:66px;display:flex;align-items:center;gap:16px;padding:0 max(18px,calc((100vw - 1400px)/2));background:color-mix(in srgb,var(--paper) 92%,transparent);border-bottom:1px solid var(--line);backdrop-filter:blur(16px)}.brand{font-weight:750;white-space:nowrap}.hint{font-size:13px;color:var(--muted)}.space{flex:1}button,input,select{font:inherit}.icon,.primary{border-radius:10px;cursor:pointer}.icon{width:40px;height:40px;border:1px solid var(--line);background:var(--paper);color:var(--ink)}.primary{padding:9px 14px;border:1px solid var(--accent);background:var(--accent);color:#fff;font-weight:650;white-space:nowrap}.layout{width:min(1400px,100%);margin:auto;display:grid;grid-template-columns:210px minmax(0,760px) minmax(260px,1fr);gap:34px;padding:38px 28px 90px}.toc{position:sticky;top:96px;align-self:start;max-height:calc(100dvh - 110px);overflow:auto}.toc p{font-size:12px;color:var(--muted)}.toc a{display:block;padding:7px 9px;color:var(--muted);text-decoration:none;border-left:2px solid transparent;font-size:14px}.toc a:hover{color:var(--accent);border-color:var(--accent)}article>h1{font-family:"Songti SC",Georgia,serif;font-size:clamp(38px,6vw,64px);line-height:1.08;letter-spacing:-.04em;max-width:12ch;margin:22px 0 30px}article>h2{font-family:"Songti SC",Georgia,serif;font-size:32px;line-height:1.25;margin:78px 0 22px}article>h3{font-size:20px;margin:42px 0 12px}article p{max-width:70ch}article li{margin:9px 0}article a{color:var(--accent);text-underline-offset:3px}.source-link{font-weight:650}.note{padding:18px 20px;border-left:4px solid var(--accent);background:var(--soft);border-radius:0 14px 14px 0}.table-wrap{overflow:auto;margin:24px 0;border:1px solid var(--line);border-radius:14px}table{border-collapse:collapse;width:100%;min-width:640px;font-size:14px}th,td{text-align:left;padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}th{background:var(--bg)}pre{overflow:auto;padding:20px;border-radius:14px;background:#262925;color:#eef0eb}.about{position:sticky;top:96px;align-self:start;padding:20px;border:1px solid var(--line);border-radius:14px;background:var(--paper)}.about h2{font-size:17px;margin:0 0 8px}.about p{font-size:14px;color:var(--muted)}.about .primary{width:100%}.drawer{position:fixed;z-index:40;top:0;right:0;width:min(680px,55vw);height:100dvh;background:var(--paper);border-left:1px solid var(--line);box-shadow:var(--shadow);transform:translateX(102%);transition:transform .28s cubic-bezier(.16,1,.3,1);display:flex;flex-direction:column}.drawer.open{transform:none}.drawer-head{display:grid;grid-template-columns:1fr auto auto;gap:10px;padding:14px 16px;border-bottom:1px solid var(--line)}.search{min-width:0;padding:10px 12px;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--ink)}.status{padding:8px 18px;color:var(--muted);font-size:13px;border-bottom:1px solid var(--line)}.source{overflow:auto;padding:18px 10px 80px;font-family:"Songti SC",Georgia,serif;line-height:2}.source-line{display:grid;grid-template-columns:48px 1fr;padding:3px 8px;border-radius:7px}.source-line.active{background:var(--hit);color:#282319}.line-number{text-align:right;padding-right:12px;color:var(--muted);font:11px/3.5 ui-monospace,monospace;text-decoration:none}.shade{position:fixed;z-index:30;inset:0;background:#10120f66;opacity:0;pointer-events:none;transition:opacity .2s}.shade.show{opacity:1;pointer-events:auto}.mobile-toc{display:none}@media(max-width:1050px){.layout{grid-template-columns:180px minmax(0,1fr)}.about{display:none}.drawer{width:72vw}}@media(max-width:760px){.top{height:60px;padding:0 14px}.hint{display:none}.layout{display:block;padding:18px}.toc{display:none}.mobile-toc{display:block;width:100%;padding:10px;margin:8px 0 26px;border:1px solid var(--line);border-radius:10px;background:var(--paper);color:var(--ink)}article>h1{font-size:40px}article>h2{font-size:27px;margin-top:56px}.drawer{width:100vw}.drawer-head{grid-template-columns:1fr auto}.drawer-head .primary{display:none}.brand{max-width:55vw;overflow:hidden;text-overflow:ellipsis}.source-line{grid-template-columns:40px 1fr;padding-inline:2px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.drawer,.shade{transition:none}}'''


def build(report: Path, source: Path, output: Path, language: str, title: str | None) -> None:
    markdown = report.read_text(encoding="utf-8")
    report_html, toc = markdown_to_html(markdown)
    if not title:
        first = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        title = re.sub(r"[*`]", "", first.group(1)) if first else report.stem
    text_lines = source.read_text(encoding="utf-8").splitlines()
    ui = UI[language]
    toc_links = "".join(f'<a href="#{a}">{html.escape(t)}</a>' for a, t in toc)
    options = "".join(f'<option value="#{a}">{html.escape(t)}</option>' for a, t in toc)
    source_html = "\n".join(
        f'<div class="source-line" id="source-L{n}" data-line="{n}"><a class="line-number" href="#source-L{n}">{n}</a><span>{html.escape(line) or "&nbsp;"}</span></div>'
        for n, line in enumerate(text_lines, 1)
    )
    labels = {k: html.escape(v) for k, v in ui.items()}
    doc = f'''<!doctype html><html lang="{language}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} - {labels['suffix']}</title><style>{CSS}</style></head><body>
<header class="top"><div class="brand">{html.escape(title)}</div><div class="hint">{labels['subtitle']}</div><div class="space"></div><button class="icon" id="theme" aria-label="{labels['theme']}">◐</button><button class="primary" id="open">{labels['source']}</button></header>
<div class="layout"><nav class="toc"><p>{labels['toc']}</p>{toc_links}</nav><main><select class="mobile-toc" id="jump"><option value="">{labels['choose']}</option>{options}</select><article>{report_html}</article></main><aside class="about"><h2>{labels['source']}</h2><p>{labels['source_help']}</p><button class="primary" id="open-side">{labels['open']}</button></aside></div>
<div class="shade" id="shade"></div><aside class="drawer" id="drawer" aria-hidden="true"><div class="drawer-head"><input class="search" id="search" aria-label="{labels['search']}" placeholder="{labels['search']}"><button class="primary" id="next">{labels['next']}</button><button class="icon" id="close" aria-label="{labels['close']}">×</button></div><div class="status" id="status">{labels['lines'].format(n=f'{len(text_lines):,}')}</div><div class="source">{source_html}</div></aside>
<script>const D=document.getElementById('drawer'),S=document.getElementById('shade'),Q=document.getElementById('search'),T=document.getElementById('status'),LS=[...document.querySelectorAll('.source-line')];let C=-1;function panel(v){{D.classList.toggle('open',v);S.classList.toggle('show',v);D.setAttribute('aria-hidden',String(!v));}}function go(n){{panel(true);const x=document.getElementById('source-L'+n);if(!x)return;document.querySelector('.source-line.active')?.classList.remove('active');x.classList.add('active');x.scrollIntoView({{block:'center',behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'auto':'smooth'}});T.textContent={ui['line']!r}.replace('{{n}}',n)}}document.addEventListener('click',e=>{{const a=e.target.closest('.source-link');if(a){{e.preventDefault();go(a.dataset.line)}}}});document.getElementById('open').onclick=()=>panel(true);document.getElementById('open-side').onclick=()=>panel(true);document.getElementById('close').onclick=()=>panel(false);S.onclick=()=>panel(false);document.addEventListener('keydown',e=>{{if(e.key==='Escape')panel(false)}});function find(){{const q=Q.value.trim().toLocaleLowerCase();if(!q)return Q.focus();for(let d=1;d<=LS.length;d++){{const i=(C+d)%LS.length;if(LS[i].innerText.toLocaleLowerCase().includes(q)){{C=i;go(LS[i].dataset.line);T.textContent={ui['found']!r}.replace('{{q}}',Q.value.trim()).replace('{{n}}',LS[i].dataset.line);return}}}}T.textContent={ui['missing']!r}.replace('{{q}}',Q.value.trim())}}document.getElementById('next').onclick=find;Q.onkeydown=e=>{{if(e.key==='Enter')find()}};document.getElementById('jump').onchange=e=>{{if(e.target.value)location.hash=e.target.value}};document.getElementById('theme').onclick=()=>{{const n=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=n;localStorage.setItem('book-theme',n)}};const saved=localStorage.getItem('book-theme');if(saved)document.documentElement.dataset.theme=saved;</script></body></html>'''
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(doc, encoding="utf-8")
    print(f"Wrote {output} with {len(text_lines)} anchored source lines")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="UTF-8 Markdown briefing")
    parser.add_argument("source", type=Path, help="UTF-8 plain-text source")
    parser.add_argument("--output", "-o", type=Path, required=True)
    parser.add_argument("--lang", choices=UI, default=None)
    parser.add_argument("--title")
    args = parser.parse_args()
    markdown = args.report.read_text(encoding="utf-8")
    language = args.lang or ("zh" if re.search(r"[\u4e00-\u9fff]", markdown[:1000]) else "en")
    build(args.report, args.source, args.output, language, args.title)


if __name__ == "__main__":
    main()
