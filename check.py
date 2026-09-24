#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三角带行业资讯 — 构建产物自检

检查项：
  1. 残留占位符 {{TOKEN}}
  2. 内链有效性（href/src 目标文件存在）
  3. 目录式 URL 的 index.html 存在
  4. sitemap.xml 与文章数一致
  5. 搜索索引与文章数一致
  6. CNAME / .nojekyll / robots.txt / 404.html 存在且内容正确
  7. 关键页面存在性
  8. 根目录无调试/临时文件残留

用法：python check.py
"""
import json
import os
import re
import sys
from urllib.parse import unquote, urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "public")
DOMAIN = "xn--ehqs60bj46a.com"

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def rel(p):
    return os.path.relpath(p, PUB).replace("\\", "/")


# ------------------------------------------------------------ 1. 遍历 HTML

# 站长验证文件（百度/必应等）是纯校验码文件，内容必须与平台给的完全一致，
# 不能加 <title>/<meta>/canonical，因此排除在 SEO 检查之外，另做专项校验。
VERIFY_PATTERNS = ("baidu_verify_", "google", "bing", "sogou_verify", "360_verify",
                   "BingSiteAuth", "baidu_verify_code", "shenma-site-verification")


def is_verify_file(name):
    low = name.lower()
    if name == "BingSiteAuth.xml":
        return True
    return any(p.lower() in low for p in VERIFY_PATTERNS)


html_files = []
verify_files = []
for dirpath, _, filenames in os.walk(PUB):
    for fn in filenames:
        if not fn.endswith(".html"):
            continue
        full = os.path.join(dirpath, fn)
        if is_verify_file(fn):
            verify_files.append(full)
        else:
            html_files.append(full)

if not html_files:
    err("public/ 下没有任何 HTML 文件，构建可能失败")
    print("FAIL: 没有 HTML 文件")
    sys.exit(1)

print(f"[1] HTML 文件数：{len(html_files)}" +
      (f"（另有 {len(verify_files)} 个站长验证文件，不计入 SEO 检查）" if verify_files else ""))

# ------------------------------------------------------------ 2. 占位符残留

placeholder_re = re.compile(r"\{\{[A-Z_0-9]+\}\}")
ph_hits = 0
for f in html_files:
    with open(f, encoding="utf-8") as fh:
        txt = fh.read()
    for m in placeholder_re.finditer(txt):
        ph_hits += 1
        err(f"{rel(f)} 残留占位符 {m.group(0)}")

print(f"[2] 占位符残留：{ph_hits} 处")

# ------------------------------------------------------------ 3. 内链检查

LINK_RE = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']')
SKIP_PREFIX = ("http://", "https://", "//", "mailto:", "tel:", "data:", "javascript:", "#")

checked = 0
broken = []
for f in html_files:
    with open(f, encoding="utf-8") as fh:
        txt = fh.read()
    for raw in LINK_RE.findall(txt):
        url = raw.strip()
        if not url or url.startswith(SKIP_PREFIX):
            continue
        path = urlparse(url).path
        if not path:
            continue
        path = unquote(path)
        checked += 1
        target = os.path.join(PUB, path.lstrip("/").replace("/", os.sep))
        if path.endswith("/"):
            target = os.path.join(target, "index.html")
        elif not os.path.splitext(target)[1]:
            target = os.path.join(target, "index.html")
        if not os.path.exists(target):
            broken.append((rel(f), url))

if broken:
    for src, url in broken:
        err(f"内链失效：{src} → {url}")
else:
    print(f"[3] 内链检查：{checked} 条链接全部有效")

# ------------------------------------------------------------ 4. sitemap 一致性

sm_path = os.path.join(PUB, "sitemap.xml")
if not os.path.exists(sm_path):
    err("sitemap.xml 不存在")
    sm_urls = []
else:
    with open(sm_path, encoding="utf-8") as fh:
        sm = fh.read()
    sm_urls = re.findall(r"<loc>([^<]+)</loc>", sm)
    if f"https://{DOMAIN}/" not in sm_urls:
        err("sitemap.xml 未包含首页 URL 或域名不正确")
    if not sm.startswith('<?xml version="1.0" encoding="UTF-8"?>'):
        err("sitemap.xml 缺少 XML 声明")

# 统计文章页：以 search-index.json 为准（避免与栏目 slug 冲突导致误判）
idx_path = os.path.join(PUB, "search-index.json")
if not os.path.exists(idx_path):
    err("search-index.json 不存在")
    idx = []
else:
    with open(idx_path, encoding="utf-8") as fh:
        idx = json.load(fh)
    # 索引里的每个 url 都要在 sitemap 里
    for it in idx:
        if f"https://{DOMAIN}{it['url']}" not in sm_urls:
            err(f"搜索索引条目未收录进 sitemap：{it['url']}")

# 反向：sitemap 里的文章 URL 也都要在索引里
idx_urls = {it["url"] for it in idx}
sm_paths = {urlparse(u).path for u in sm_urls}
_missing_in_idx = [
    p for p in sm_paths
    if p.strip("/").count("/") == 1
    and p.split("/")[1] not in ("news", "category", "search", "sitemap")
    and p not in idx_urls
]
if _missing_in_idx:
    err(f"sitemap 中的文章未进搜索索引：{_missing_in_idx}")

# 同时统计磁盘上的文章页目录数（交叉校验）
disk_articles = []
for seg in ("basics", "models", "guide", "news", "faq"):
    d = os.path.join(PUB, seg)
    if not os.path.isdir(d):
        continue
    for name in os.listdir(d):
        if os.path.isdir(os.path.join(d, name)) and os.path.exists(
            os.path.join(d, name, "index.html")
        ):
            disk_articles.append(f"/{seg}/{name}/")

art_urls = idx_urls
idx_n = len(idx)

print(f"[4] sitemap URL 数：{len(sm_urls)}，其中文章页 {len(disk_articles)} 篇")
print(f"[5] 搜索索引条目：{idx_n} 篇")

if idx_n != len(disk_articles):
    err(f"搜索索引（{idx_n} 篇）与磁盘文章页（{len(disk_articles)} 篇）不一致")

for p in disk_articles:
    if f"https://{DOMAIN}{p}" not in sm_urls:
        err(f"文章页未收录进 sitemap：{p}")

# ------------------------------------------------------------ 5. 关键文件

must_have = {
    "index.html": None,
    "CNAME": DOMAIN,
    ".nojekyll": "",
    "robots.txt": "Sitemap:",
    "404.html": "404",
    "sitemap.xml": "<urlset",
    "search-index.json": "[",
    "specs/index.html": "速查表",
    "news/index.html": None,
    "search/index.html": None,
    "about/index.html": None,
    "sitemap/index.html": None,
    "assets/style.css": None,
    "assets/main.js": None,
    "assets/favicon.svg": None,
}
for path, needle in must_have.items():
    full = os.path.join(PUB, path.replace("/", os.sep))
    if not os.path.exists(full):
        err(f"缺少文件：{path}")
        continue
    if needle:
        with open(full, encoding="utf-8", errors="ignore") as fh:
            txt = fh.read()
        if needle not in txt:
            err(f"{path} 内容校验失败，未找到 {needle!r}")

# CNAME 值精确校验
cname_p = os.path.join(PUB, "CNAME")
if os.path.exists(cname_p):
    with open(cname_p, encoding="utf-8") as fh:
        cval = fh.read().strip()
    if cval != DOMAIN:
        err(f"CNAME 内容为 {cval!r}，期望 {DOMAIN!r}")

# ------------------------------------------------------------ 5b. 站长验证文件

# 这些文件必须：① 存在于 public/ 根目录；② 内容非空；③ 没被 HTML 模板污染
for full in verify_files:
    name = rel(full)
    with open(full, encoding="utf-8", errors="ignore") as fh:
        vtxt = fh.read()
    if not vtxt.strip():
        err(f"站长验证文件为空：{name}")
        continue
    if "<html" in vtxt.lower() or "<!doctype" in vtxt.lower():
        err(f"站长验证文件被模板污染（含 HTML 标签，会导致平台校验失败）：{name}")
    print(f"[5b] 站长验证文件：{name}（{len(vtxt.strip())} 字符）")

# ------------------------------------------------------------ 6. 分类页存在性

with open(os.path.join(ROOT, "categories.json"), encoding="utf-8") as fh:
    cats = json.load(fh)
for c in cats:
    p = os.path.join(PUB, "category", c["slug"], "index.html")
    if not os.path.exists(p):
        err(f"缺少栏目页：/category/{c['slug']}/")

# ------------------------------------------------------------ 7. 根目录残留

for fn in os.listdir(PUB):
    if fn.startswith("_") or fn.endswith((".tmp", ".bak", ".tmp_ignore", ".orig")):
        err(f"public/ 根目录残留调试/临时文件：{fn}")

# ------------------------------------------------------------ 8. SEO 基础项

no_title = 0
no_desc = 0
no_canonical = 0
for f in html_files:
    with open(f, encoding="utf-8") as fh:
        txt = fh.read()
    if "<title>" not in txt:
        no_title += 1
        err(f"{rel(f)} 缺少 <title>")
    if 'name="description"' not in txt:
        no_desc += 1
        err(f"{rel(f)} 缺少 meta description")
    if 'rel="canonical"' not in txt:
        no_canonical += 1
        err(f"{rel(f)} 缺少 canonical")

if no_title == 0 and no_desc == 0 and no_canonical == 0:
    print(f"[6] SEO 基础项：{len(html_files)} 页均有 title / description / canonical")

# ------------------------------------------------------------ 9. 标题长度（中文站建议 ≤30 全角字）

long_titles = []
for f in html_files:
    with open(f, encoding="utf-8") as fh:
        txt = fh.read()
    m = re.search(r"<title>(.*?)</title>", txt, re.S)
    if m:
        t = m.group(1).strip()
        if len(t) > 34:
            long_titles.append((rel(f), len(t), t))
if long_titles:
    for f, n, t in long_titles:
        warn(f"标题偏长（{n} 字）：{f} — {t}")

# ------------------------------------------------------------ 输出

print()
print("=" * 62)
if errors:
    print(f"  自检未通过：{len(errors)} 个问题")
    for e in errors:
        print(f"    ✗ {e}")
else:
    print("  自检通过：所有检查项正常")
if warnings:
    print(f"  提示：{len(warnings)} 条")
    for w in warnings:
        print(f"    ! {w}")
print("=" * 62)

sys.exit(1 if errors else 0)
