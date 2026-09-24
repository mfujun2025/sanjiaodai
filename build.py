#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三角带行业资讯 — 静态站构建脚本

用法：
    python build.py

输入：
    site.json         站点元信息（名称、域名、导航）
    categories.json   栏目定义
    specs.json        规格速查表数据
    content/**.md     文章（YAML front matter + Markdown 正文）
    content/about.md  关于页
    templates/*.html  页面模板（{{TOKEN}} 占位符）
    static/**         静态资源，递归平铺复制到 public/

输出：
    public/           可直接部署的静态站点

设计约定：
    - 不清空 public/，覆盖式写入（本机 Python 删除操作被路由到回收站）
    - 模板用 {{TOKEN}} + str.replace，不用 .format（会被 CSS 花括号炸掉）
    - 所有文件写 UTF-8
"""
import json
import os
import re
import shutil
import sys
import html as html_mod
from datetime import date

import markdown

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "public")
TPL = os.path.join(ROOT, "templates")
CONTENT = os.path.join(ROOT, "content")
STATIC = os.path.join(ROOT, "static")

# ------------------------------------------------------------------ 工具


def read_json(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def tpl(name):
    return read(os.path.join(TPL, name))


def fill(template, mapping):
    out = template
    for k, v in mapping.items():
        out = out.replace("{{" + k + "}}", str(v))
    return out


def esc(s):
    return html_mod.escape(str(s), quote=True)


def parse_front(text):
    """解析简单 YAML front matter，返回 (meta_dict, body_md)。"""
    meta = {}
    body = text
    m = re.match(r"^\s*---\s*\n(.*?)\n---\s*\n?(.*)$", text, re.S)
    if m:
        block, body = m.group(1), m.group(2)
        for line in block.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            if val.lower() in ("true", "yes"):
                val = True
            elif val.lower() in ("false", "no"):
                val = False
            meta[key] = val
    return meta, body.strip()


def md_to_html(md_text):
    """Markdown → HTML，表格外包 .table-scroll 以便移动端横向滚动。"""
    out = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "attr_list"],
        output_format="html5",
    )
    out = out.replace("<table>", '<div class="table-scroll"><table>')
    out = out.replace("</table>", "</table></div>")
    # 表格统一加类名
    out = out.replace('<div class="table-scroll"><table>',
                      '<div class="table-scroll"><table class="data-table">')
    return out


def plain_text(md_text):
    """正文 → 纯文本，用于搜索索引与阅读时长估算。"""
    t = re.sub(r"```.*?```", " ", md_text, flags=re.S)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)
    t = re.sub(r"^[>#\-\*\|\s]+", " ", t, flags=re.M)
    t = re.sub(r"\|", " ", t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{2,}", "\n", t)
    return t.strip()


def read_minutes(md_text):
    n = len(plain_text(md_text))
    mins = max(1, round(n / 400))
    return f"约 {mins} 分钟阅读"


def slugify_anchor(text):
    """标题 → 锚点 id（保留中文，去掉标点）。"""
    t = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.U)
    return t.strip("-").lower() or "section"


# ------------------------------------------------------------------ 载入配置

SITE = read_json("site.json")
CATS = read_json("categories.json")
SPECS = read_json("specs.json")

BASE = SITE["base_url"].rstrip("/")
DOMAIN = SITE["domain"]
DOMAIN_CN = SITE["domain_cn"]
SITE_NAME = SITE["name"]
SITE_SHORT = SITE.get("short_name", SITE_NAME)
AUTHOR = SITE["author"]

CAT_BY_SLUG = {c["slug"]: c for c in CATS}
CAT_ORDER = [c["slug"] for c in CATS]


# ------------------------------------------------------------------ 载入文章

def load_articles():
    items = []
    for cat_slug in CAT_ORDER:
        d = os.path.join(CONTENT, cat_slug)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".md"):
                continue
            raw = read(os.path.join(d, fn))
            meta, body = parse_front(raw)
            slug = meta.get("slug") or fn[:-3]
            cat = meta.get("category") or cat_slug
            item = {
                "slug": slug,
                "url": f"/{cat}/{slug}/",
                "category": cat,
                "category_name": CAT_BY_SLUG.get(cat, {}).get("name", cat),
                "title": meta.get("title", slug),
                "date": str(meta.get("date", "")),
                "desc": meta.get("desc", ""),
                "keywords": meta.get("keywords", ""),
                "featured": bool(meta.get("featured", False)),
                "author": meta.get("author", AUTHOR),
                "md": body,
                "html": md_to_html(body),
                "plain": plain_text(body),
            }
            items.append(item)
    items.sort(key=lambda x: (x["date"], x["slug"]), reverse=True)
    return items


ARTICLES = load_articles()
BY_CAT = {c: [a for a in ARTICLES if a["category"] == c] for c in CAT_ORDER}


# ------------------------------------------------------------------ 公共片段

def nav_html(active):
    parts = []
    for item in SITE["nav"]:
        url = item["url"]
        cls = "is-active" if url == active else ""
        parts.append(f'<a href="{url}" class="{cls}">{esc(item["text"])}</a>')
    return "\n      ".join(parts)


def footer_links_html():
    return "\n        ".join(
        f'<li><a href="{i["url"]}">{esc(i["text"])}</a></li>' for i in SITE["footer_links"]
    )


def jsonld_website():
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": SITE_NAME,
        "url": BASE + "/",
        "description": SITE["description"],
        "inLanguage": "zh-CN",
        "potentialAction": {
            "@type": "SearchAction",
            "target": BASE + "/search/?q={search_term_string}",
            "query-input": "required name=search_term_string",
        },
    }, ensure_ascii=False, indent=None, separators=(",", ":"))


def jsonld_article(a):
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": a["title"],
        "description": a["desc"],
        "datePublished": a["date"],
        "dateModified": a["date"],
        "inLanguage": "zh-CN",
        "author": {"@type": "Organization", "name": a["author"]},
        "publisher": {"@type": "Organization", "name": SITE_NAME},
        "mainEntityOfPage": {"@type": "WebPage", "@id": BASE + a["url"]},
        "articleSection": a["category_name"],
        "keywords": a["keywords"],
    }, ensure_ascii=False, separators=(",", ":"))


def jsonld_breadcrumb(crumbs):
    items = []
    for i, (name, url) in enumerate(crumbs, start=1):
        entry = {"@type": "ListItem", "position": i, "name": name}
        if url:
            entry["item"] = BASE + url
        items.append(entry)
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": items,
    }, ensure_ascii=False, separators=(",", ":"))


def page(title, desc, path, content, active="", keywords="", jsonld="", robots="index,follow"):
    """把内容塞进 layout，返回完整 HTML。path 形如 /news/ 或 /。"""
    canonical = BASE + path
    return fill(tpl("layout.html"), {
        "TITLE": esc(title),
        "DESC": esc(desc),
        "KEYWORDS_META": f'<meta name="keywords" content="{esc(keywords)}">' if keywords else "",
        "AUTHOR": esc(AUTHOR),
        "ROBOTS": robots,
        "CANONICAL": canonical,
        "SITE_NAME": esc(SITE_NAME),
        "SITE_DESC": esc(SITE["description"]),
        "DOMAIN": DOMAIN,
        "DOMAIN_CN": esc(DOMAIN_CN),
        "ICP_NOTE": esc(SITE["icp_note"]),
        "NAV": nav_html(active),
        "FOOTER_LINKS": footer_links_html(),
        "JSONLD": f'<script type="application/ld+json">{jsonld}</script>' if jsonld else "",
        "OG_IMAGE": f'<meta property="og:image" content="{BASE}/assets/og-cover.svg">',
        "CONTENT": content,
    })


# ------------------------------------------------------------------ 卡片组件

def card_html(a, feature=False):
    cls = "card card-feature" if feature else "card"
    kw = a["keywords"].split(",")[0] if a["keywords"] else a["category_name"]
    return (
        f'<article class="{cls}">\n'
        f'  <div class="card-top">\n'
        f'    <a class="card-cat" href="/category/{a["category"]}/">{esc(a["category_name"])}</a>\n'
        f'    <span class="card-date">{esc(a["date"])}</span>\n'
        f'  </div>\n'
        f'  <h3><a href="{a["url"]}">{esc(a["title"])}</a></h3>\n'
        f'  <p>{esc(a["desc"])}</p>\n'
        f'  <div class="card-foot">\n'
        f'    <span class="card-kw">{esc(kw)}</span>\n'
        f'    <a class="card-more" href="{a["url"]}">阅读全文 →</a>\n'
        f'  </div>\n'
        f'</article>'
    )


def cards_html(items, feature_first=False):
    out = []
    for i, a in enumerate(items):
        out.append(card_html(a, feature=(feature_first and i == 0)))
    return "\n".join(out)


def list_item_html(a):
    return (
        f'<a class="list-item" href="{a["url"]}">'
        f'<span class="li-dot" aria-hidden="true"></span>'
        f'<span class="li-title">{esc(a["title"])}</span>'
        f'<span class="li-date">{esc(a["date"])}</span>'
        f'</a>'
    )


# ------------------------------------------------------------------ 生成：首页

def build_index():
    cat_cards = []
    for c in CATS:
        n = len(BY_CAT.get(c["slug"], []))
        cat_cards.append(
            f'<a class="cat-card" href="/category/{c["slug"]}/">\n'
            f'  <span class="cat-icon" aria-hidden="true">{esc(c["icon"])}</span>\n'
            f'  <h3>{esc(c["name"])}</h3>\n'
            f'  <p>{esc(c["desc"])}</p>\n'
            f'  <span class="cat-count">{n} 篇内容 →</span>\n'
            f'</a>'
        )

    featured = [a for a in ARTICLES if a["featured"]][:4]
    if len(featured) < 4:
        for a in ARTICLES:
            if a not in featured:
                featured.append(a)
            if len(featured) >= 4:
                break

    latest = [a for a in ARTICLES if a not in featured][:6]
    if len(latest) < 6:
        for a in ARTICLES:
            if a not in latest and a not in featured:
                latest.append(a)
        latest = latest[:6]

    content = fill(tpl("index.html"), {
        "STAT_ARTICLES": len(ARTICLES),
        "STAT_CATS": len(CATS),
        "STAT_TABLES": sum(len(SPECS[k]["rows"]) for k in SPECS if isinstance(SPECS.get(k), dict) and "rows" in SPECS[k]),
        "CATEGORY_CARDS": "\n      ".join(cat_cards),
        "FEATURED_CARDS": cards_html(featured, feature_first=True),
        "LATEST_CARDS": cards_html(latest),
    })

    out = page(
        title=f"{SITE_NAME} — 三角带（V带）选型、型号速查与维护指南",
        desc=SITE["description"],
        path="/",
        content=content,
        active="/",
        keywords=SITE["keywords"],
        jsonld=jsonld_website(),
    )
    write(os.path.join(PUB, "index.html"), out)
    return 1


# ------------------------------------------------------------------ 生成：文章详情页

def build_article(a):
    # 目录 + 正文锚点注入
    headings = re.findall(r"<h([23])>(.*?)</h\1>", a["html"], flags=re.S)
    toc_items = []
    used = {}
    for level, raw in headings:
        text = re.sub(r"<[^>]+>", "", raw).strip()
        if not text:
            continue
        anchor = slugify_anchor(text)
        if anchor in used:
            used[anchor] += 1
            anchor = f"{anchor}-{used[anchor]}"
        else:
            used[anchor] = 0
        toc_items.append((level, text, anchor))

    # 用正则按顺序替换标题，注入 id
    body = a["html"]
    counter = {"i": 0}

    def repl(m):
        level, text, anchor = toc_items[counter["i"]] if counter["i"] < len(toc_items) else (m.group(1), m.group(2), "")
        counter["i"] += 1
        return f'<h{level} id="{anchor}">{text}</h{level}>'

    if toc_items:
        body = re.sub(r"<h([23])>(.*?)</h\1>", repl, body, flags=re.S)

    toc_html = ""
    if toc_items:
        links = []
        for level, text, anchor in toc_items:
            cls = "lv3" if level == "3" else ""
            links.append(f'<a class="{cls}" href="#{anchor}">{esc(text)}</a>')
        toc_html = (
            '<div class="side-box"><h3>本文目录</h3><nav class="toc">'
            + "\n".join(links)
            + "</nav></div>"
        )

    # 关键词标签
    tags = []
    for k in [x.strip() for x in a["keywords"].split(",") if x.strip()]:
        tags.append(f'<a class="tag" href="/search/?q={__import__("urllib.parse", fromlist=["quote"]).quote(k)}">{esc(k)}</a>')
    tags_html = "\n      ".join(tags)

    # 同栏文章
    siblings = [x for x in BY_CAT.get(a["category"], []) if x["slug"] != a["slug"]][:6]
    side_links = "\n        ".join(
        f'<a href="{x["url"]}">{esc(x["title"])}</a>' for x in siblings
    ) or '<span class="card-kw">暂无其他文章</span>'

    # 相关阅读：同栏目优先，不足补最新
    related = siblings[:3]
    if len(related) < 3:
        for x in ARTICLES:
            if x["slug"] != a["slug"] and x not in related:
                related.append(x)
            if len(related) >= 3:
                break
    related_html = ""
    if related:
        related_html = (
            '<section class="related">\n<h2>相关阅读</h2>\n<div class="card-grid">\n'
            + cards_html(related)
            + "\n</div>\n</section>"
        )

    content = fill(tpl("article.html"), {
        "CAT_SLUG": a["category"],
        "CAT_NAME": esc(a["category_name"]),
        "CRUMB_MID": (
            f'<a href="/category/{a["category"]}/">{esc(a["category_name"])}</a>'
            f'<span class="sep">/</span>'
        ),
        "CAT_LINK": f'<a class="am-cat" href="/category/{a["category"]}/">{esc(a["category_name"])}</a>',
        "CRUMB_TITLE": esc(a["title"]),
        "ARTICLE_TITLE": esc(a["title"]),
        "DATE": esc(a["date"]),
        "AUTHOR": esc(a["author"]),
        "READ_TIME": read_minutes(a["md"]),
        "BODY": body,
        "TAGS": tags_html,
        "RELATED": related_html,
        "TOC_BOX": toc_html,
        "SIDE_SIBLINGS": (
            '<div class="side-box"><h3>同栏目文章</h3><div class="side-links">'
            + side_links + "</div></div>"
        ) if siblings else "",
    })

    jsonld = (
        '<script type="application/ld+json">' + jsonld_article(a) + "</script>"
        + '<script type="application/ld+json">'
        + jsonld_breadcrumb([("首页", "/"), (a["category_name"], f'/category/{a["category"]}/'), (a["title"], None)])
        + "</script>"
    )

    out = page(
        title=f'{a["title"]} | {SITE_SHORT}',
        desc=a["desc"],
        path=a["url"],
        content=content,
        active=f'/category/{a["category"]}/',
        keywords=a["keywords"],
        jsonld=jsonld,
    )
    write(os.path.join(PUB, a["category"], a["slug"], "index.html"), out)
    return 1


# ------------------------------------------------------------------ 生成：栏目页 / 全量列表 / 搜索 / 关于 / 地图

def build_category(c):
    items = BY_CAT.get(c["slug"], [])
    filters = ['<a class="is-active" href="/news/">全部</a>']
    for cc in CATS:
        filters.append(f'<a href="/category/{cc["slug"]}/">{esc(cc["name"])}</a>')

    content = fill(tpl("list.html"), {
        "CRUMB_TAIL": f'<span>{esc(c["name"])}</span>',
        "PAGE_TITLE": esc(c["name"]),
        "PAGE_DESC": esc(c["desc"]),
        "PAGE_COUNT": f'共 {len(items)} 篇内容',
        "FILTERS": "\n      ".join(filters),
        "CARDS": cards_html(items, feature_first=True) if items else '<p class="sr-empty">该栏目暂无内容。</p>',
    })

    jsonld = (
        '<script type="application/ld+json">'
        + jsonld_breadcrumb([("首页", "/"), (c["name"], None)])
        + "</script>"
    )

    out = page(
        title=f'{c["name"]} | {SITE_SHORT}',
        desc=c["desc"],
        path=f'/category/{c["slug"]}/',
        content=content,
        active=f'/category/{c["slug"]}/',
        keywords=c["keywords"],
        jsonld=jsonld,
    )
    write(os.path.join(PUB, "category", c["slug"], "index.html"), out)
    return 1


def build_all_news():
    filters = ['<a class="is-active" href="/news/">全部</a>']
    for cc in CATS:
        filters.append(f'<a href="/category/{cc["slug"]}/">{esc(cc["name"])}</a>')

    groups = []
    years = sorted({a["date"][:4] for a in ARTICLES if a["date"]}, reverse=True)
    for y in years:
        rows = [a for a in ARTICLES if a["date"].startswith(y)]
        groups.append(
            f'<div class="map-group"><h2>{y} 年（{len(rows)} 篇）</h2>'
            '<div class="card-grid">' + cards_html(rows) + "</div></div>"
        )

    content = fill(tpl("list.html"), {
        "CRUMB_TAIL": "<span>全部内容</span>",
        "PAGE_TITLE": "全部内容",
        "PAGE_DESC": "本站全部技术文章与行业资讯，按年份分组，最新在前。可按栏目筛选，也可使用站内搜索按关键词定位。",
        "PAGE_COUNT": f'共 {len(ARTICLES)} 篇内容',
        "FILTERS": "\n      ".join(filters),
        "CARDS": "",
    })
    # 全量列表页用「年份分组」替换掉卡片区
    content = re.sub(
        r'<section class="section">\s*<div class="wrap">\s*<div class="card-grid">\s*</div>\s*</div>\s*</section>',
        '<section class="section"><div class="wrap">' + "".join(groups) + "</div></section>",
        content,
    )
    if not groups:
        content = content.replace('<div class="card-grid">', '<div class="card-grid">', 1)

    out = page(
        title=f"全部内容 | {SITE_SHORT}",
        desc="本站全部三角带（V带）技术文章与行业资讯，按年份分组浏览。",
        path="/news/",
        content=content,
        active="/news/",
        keywords="三角带文章,三角带资讯,V带技术资料",
    )
    write(os.path.join(PUB, "news", "index.html"), out)
    return 1


def build_search():
    content = tpl("search.html")
    out = page(
        title=f"站内搜索 | {SITE_SHORT}",
        desc="检索本站全部三角带（V带）技术文章，支持多关键词匹配标题、关键词、摘要与正文。",
        path="/search/",
        content=content,
        active="/search/",
        keywords="三角带搜索,V带资料检索",
        robots="noindex,follow",
    )
    write(os.path.join(PUB, "search", "index.html"), out)
    return 1


def build_about():
    meta, body = parse_front(read(os.path.join(CONTENT, "about.md")))
    title = meta.get("title", "关于本站")
    desc = meta.get("desc", f"{SITE_NAME}的定位、内容范围、内容原则与免责声明。")
    content = fill(tpl("article.html"), {
        "CAT_SLUG": "about",
        "CAT_NAME": "关于本站",
        "CRUMB_MID": "",
        "CAT_LINK": '<span class="am-cat">关于本站</span>',
        "CRUMB_TITLE": esc(title),
        "ARTICLE_TITLE": esc(title),
        "DATE": "2026-09-24",
        "AUTHOR": esc(AUTHOR),
        "READ_TIME": read_minutes(body),
        "BODY": md_to_html(body),
        "TAGS": "",
        "RELATED": "",
        "TOC_BOX": "",
        "SIDE_SIBLINGS": '<div class="side-box"><h3>快速入口</h3><div class="side-links">'
                         '<a href="/sitemap/">网站地图</a>'
                         '<a href="/specs/">型号规格速查表</a>'
                         '<a href="/category/faq/">常见问题</a>'
                         '<a href="/category/guide/">选型与安装维护</a>'
                         "</div></div>",
    })
    out = page(
        title=f"{title} | {SITE_SHORT}",
        desc=desc,
        path="/about/",
        content=content,
        active="/about/",
        keywords="关于三角带行业资讯,内容原则,免责声明",
        jsonld='<script type="application/ld+json">'
               + jsonld_breadcrumb([("首页", "/"), (title, None)]) + "</script>",
    )
    write(os.path.join(PUB, "about", "index.html"), out)
    return 1


# ------------------------------------------------------------------ 生成：速查表

def spec_block(key):
    d = SPECS[key]
    head = "".join(f"<th>{esc(h)}</th>" for h in d["headers"])
    rows = []
    for r in d["rows"]:
        tds = "".join(f"<td>{esc(c)}</td>" for c in r)
        rows.append(f"<tr>{tds}</tr>")
    return (
        f'<div class="spec-block" id="{key}">\n'
        f'  <h2>{esc(d["title"])}</h2>\n'
        f'  <p class="spec-sub">{esc(d["subtitle"])}</p>\n'
        f'  <div class="table-scroll">\n'
        f'    <table class="data-table">\n'
        f'      <thead><tr>{head}</tr></thead>\n'
        f'      <tbody>{"".join(rows)}</tbody>\n'
        f'    </table>\n'
        f'  </div>\n'
        f'</div>'
    )


SPEC_KEYS = ["normal_v", "narrow_v", "us_narrow_v", "length_basis",
             "structure_codes", "min_pulley", "materials", "troubleshoot", "checklist"]


def build_specs():
    blocks = "\n".join(spec_block(k) for k in SPEC_KEYS if k in SPECS)
    content = fill(tpl("specs.html"), {
        "CRUMB_TITLE": "<span>型号规格速查表</span>",
        "PAGE_TITLE": "三角带型号规格速查表",
        "PAGE_DESC": "普通 V 带 Y/Z/A/B/C/D/E 与窄 V 带 SPZ/SPA/SPB/SPC 的截面尺寸、长度范围、长度基准、最小带轮直径、胶料耐温耐油与失效现象速查。可打印用于现场比对。",
        "SPEC_BLOCKS": blocks,
    })
    out = page(
        title=f"三角带型号规格速查表 | {SITE_SHORT}",
        desc="三角带型号规格速查表：普通V带 Y/Z/A/B/C/D/E 与窄V带 SPZ/SPA/SPB/SPC 截面尺寸、顶宽节宽高度、长度范围与基准、小带轮最小直径、胶料耐温耐油对照、失效现象速查。",
        path="/specs/",
        content=content,
        active="/specs/",
        keywords="三角带规格表,三角带型号对照,A型三角带尺寸,B型三角带尺寸,SPZ,SPA,SPB,SPC,窄V带规格,长度基准",
        jsonld='<script type="application/ld+json">'
               + jsonld_breadcrumb([("首页", "/"), ("型号规格速查表", None)]) + "</script>",
    )
    write(os.path.join(PUB, "specs", "index.html"), out)
    return 1


# ------------------------------------------------------------------ 生成：网站地图 + sitemap.xml + robots

def build_sitemap_page():
    main_pages = [
        ("/", "首页", ""),
        ("/news/", f'全部内容（{len(ARTICLES)} 篇）', ""),
        ("/specs/", "型号规格速查表", ""),
        ("/search/", "站内搜索", ""),
        ("/sitemap/", "网站地图", ""),
        ("/about/", "关于本站", ""),
    ]
    main_html = "\n        ".join(
        f'<li><a href="{u}">{esc(t)}</a><span class="map-meta">{esc(m)}</span></li>'
        for u, t, m in main_pages
    )

    groups = []
    for c in CATS:
        rows = BY_CAT.get(c["slug"], [])
        lis = "\n          ".join(
            f'<li><a href="{a["url"]}">{esc(a["title"])}</a>'
            f'<span class="map-meta">{esc(a["date"])}</span></li>'
            for a in rows
        )
        groups.append(
            f'<div class="map-group">\n'
            f'  <h2>{esc(c["name"])}（{len(rows)} 篇）</h2>\n'
            f'  <ul class="map-list">\n          {lis}\n  </ul>\n'
            f'</div>'
        )

    total_pages = len(ARTICLES) + len(CATS) + 6
    content = fill(tpl("sitemap.html"), {
        "TOTAL_PAGES": total_pages,
        "MAIN_PAGES": main_html,
        "SITEMAP_CONTENT": "\n    ".join(groups),
    })
    out = page(
        title=f"网站地图 | {SITE_SHORT}",
        desc=f"{SITE_NAME}全部页面与文章一览，共 {total_pages} 个页面，按栏目分组。",
        path="/sitemap/",
        content=content,
        active="/sitemap/",
        keywords="网站地图,三角带文章列表",
    )
    write(os.path.join(PUB, "sitemap", "index.html"), out)
    return total_pages


def build_sitemap_xml():
    urls = [
        ("/", "1.0"),
        ("/news/", "0.8"),
        ("/specs/", "0.9"),
        ("/about/", "0.4"),
        ("/sitemap/", "0.3"),
    ]
    for c in CATS:
        urls.append((f'/category/{c["slug"]}/', "0.7"))
    entries = "\n".join(
        f'  <url>\n    <loc>{BASE}{u}</loc>\n    <changefreq>weekly</changefreq>\n'
        f'    <priority>{p}</priority>\n  </url>'
        for u, p in urls
    )
    art_entries = "\n".join(
        f'  <url>\n    <loc>{BASE}{a["url"]}</loc>\n    <lastmod>{a["date"]}</lastmod>\n'
        f'    <changefreq>monthly</changefreq>\n    <priority>0.6</priority>\n  </url>'
        for a in ARTICLES
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + entries + "\n" + art_entries + "\n</urlset>\n"
    )
    write(os.path.join(PUB, "sitemap.xml"), xml)

    robots = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /search/\n\n"
        f"Sitemap: {BASE}/sitemap.xml\n"
    )
    write(os.path.join(PUB, "robots.txt"), robots)
    return len(urls) + len(ARTICLES)


# ------------------------------------------------------------------ 生成：搜索索引 / 404 / CNAME / .nojekyll

def build_search_index():
    data = []
    for a in ARTICLES:
        data.append({
            "title": a["title"],
            "url": a["url"],
            "category": a["category_name"],
            "category_name": a["category_name"],
            "date": a["date"],
            "desc": a["desc"],
            "keywords": a["keywords"],
            "body": a["plain"][:2400],
        })
    write(os.path.join(PUB, "search-index.json"),
          json.dumps(data, ensure_ascii=False, separators=(",", ":")))
    return len(data)


def build_404():
    content = tpl("404.html")
    out = page(
        title=f"页面不存在 | {SITE_SHORT}",
        desc="你访问的页面不存在，可返回首页或从型号规格速查表、网站地图继续浏览。",
        path="/404.html",
        content=content,
        robots="noindex,follow",
    )
    write(os.path.join(PUB, "404.html"), out)
    return 1


def build_static_files():
    """CNAME 与 .nojekyll：必须由构建产出，否则会被部署时的覆盖式 tree 抹掉。"""
    write(os.path.join(PUB, "CNAME"), DOMAIN + "\n")
    write(os.path.join(PUB, ".nojekyll"), "")
    return 2


def copy_static():
    n = 0
    if not os.path.isdir(STATIC):
        return 0
    for dirpath, _, filenames in os.walk(STATIC):
        for fn in filenames:
            if fn.startswith("."):
                continue
            src = os.path.join(dirpath, fn)
            dst = os.path.join(PUB, os.path.relpath(src, STATIC))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(src, dst)
            n += 1
    return n


# ------------------------------------------------------------------ 主流程

def main():
    os.makedirs(PUB, exist_ok=True)

    pages = 0
    pages += build_index()
    for a in ARTICLES:
        pages += build_article(a)
    for c in CATS:
        pages += build_category(c)
    pages += build_all_news()
    pages += build_search()
    pages += build_about()
    pages += build_specs()
    total_pages = build_sitemap_page()
    pages += 1
    pages += build_404()

    n_xml = build_sitemap_xml()
    n_idx = build_search_index()
    n_sf = build_static_files()
    n_static = copy_static()

    print("=" * 62)
    print(f"  站点：{SITE_NAME}  ({DOMAIN_CN} / {DOMAIN})")
    print("=" * 62)
    print(f"  文章数        : {len(ARTICLES)}")
    print(f"  栏目数        : {len(CATS)}")
    for c in CATS:
        print(f"      - {c['name']:<16} {len(BY_CAT[c['slug']]):>2} 篇")
    print(f"  HTML 页面数   : {pages + 1}")
    print(f"  网站地图声明  : {n_xml} 条 URL（页面 + 文章）")
    print(f"  搜索索引条目  : {n_idx} 篇")
    print(f"  速查表格      : {len(SPEC_KEYS)} 张 / "
          f"{sum(len(SPECS[k]['rows']) for k in SPEC_KEYS if k in SPECS)} 行数据")
    print(f"  静态资源      : {n_static} 个 + CNAME/.nojekyll")
    print(f"  输出目录      : {os.path.relpath(PUB, ROOT)}/")
    print("=" * 62)
    print("  构建完成。本地预览：")
    print(f'    python -m http.server 8899 --directory "{PUB}"')
    print("=" * 62)


if __name__ == "__main__":
    main()
