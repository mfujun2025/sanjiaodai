#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
三角带行业资讯 — 发布脚本（GitHub Git Data API）

为什么不用 git push：
    本机装有网络加速工具时，`git push` 会被 SIGTERM 直接拦截、无任何输出。
    走 Git Data API（blobs → tree → ref）可绕开该问题。

用法：
    python deploy.py --source-only    # 仅推送源码到 main
    python deploy.py                  # 推送源码到 main + 构建产物到 gh-pages
    python deploy.py --pages          # 额外尝试启用 Pages 并绑定域名（需 Pages 权限）

凭据（按顺序取，取到即用）：
    1. 环境变量 GITHUB_TOKEN
    2. ~/.git-credentials 中匹配 github.com 的条目

Token 权限：
    - 推送代码：Contents = Read and write
    - 启用 Pages / 绑域名：Pages = Read and write
"""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "public")
API = "https://api.github.com"

OWNER = "mfujun2025"
REPO = "sanjiaodai"
SRC_BRANCH = "main"
PUB_BRANCH = "gh-pages"
DOMAIN = "xn--ehqs60bj46a.com"

# 推送源码时排除的内容
SRC_EXCLUDE_DIRS = {"public", ".git", "__pycache__", ".cdp-profile-1", ".archive-sanjiaodai-old"}
SRC_EXCLUDE_EXT = {".pyc", ".pyo", ".log", ".tmp", ".bak"}
SRC_EXCLUDE_FILES = {"verify-out.json", "verify-err.txt", "http.log", "chrome.log",
                     "package.json", "package-lock.json"}
SRC_EXCLUDE_PREFIX = ("_",)


# ---------------------------------------------------------------- 凭据

def get_token():
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    cred = os.path.expanduser("~/.git-credentials")
    if os.path.exists(cred):
        with open(cred, encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = re.match(r"https?://([^:]+):([^@]+)@github\.com", line.strip())
                if m:
                    return m.group(2)
    return None


# ---------------------------------------------------------------- HTTP

def api(method, path, token, body=None, raw=False):
    url = path if path.startswith("http") else API + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "sanjiaodai-deploy")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            raw_body = r.read()
            if raw:
                return r.status, raw_body
            return r.status, (json.loads(raw_body) if raw_body else {})
    except urllib.error.HTTPError as e:
        body_txt = e.read().decode("utf-8", "ignore")
        if raw:
            return e.code, body_txt
        try:
            return e.code, json.loads(body_txt)
        except Exception:
            return e.code, {"message": body_txt[:400]}


# ---------------------------------------------------------------- 文件收集

def collect_src():
    files = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [
            d for d in dirnames
            if d not in SRC_EXCLUDE_DIRS and not d.startswith(".archive-")
        ]
        for fn in filenames:
            if fn in SRC_EXCLUDE_FILES:
                continue
            if fn.startswith(SRC_EXCLUDE_PREFIX):
                continue
            if os.path.splitext(fn)[1] in SRC_EXCLUDE_EXT:
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, ROOT).replace("\\", "/")
            # 隐藏文件：只放行 .gitignore / .nojekyll，其余跳过
            if os.path.basename(rel).startswith(".") and os.path.basename(rel) not in (".gitignore", ".nojekyll"):
                continue
            files.append(full)
    return files


def collect_pub():
    files = []
    for dirpath, _, filenames in os.walk(PUB):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, PUB).replace("\\", "/")
            if os.path.basename(rel).startswith(".") and os.path.basename(rel) != ".nojekyll":
                continue
            files.append(full)
    return files


# ---------------------------------------------------------------- 推送

def push(token, branch, file_paths, base_dir, message):
    # 1) 取分支 head（不存在则用 --create 激活）
    st, ref = api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{branch}", token)
    parents = []
    base_tree = None
    if st == 200:
        parents = [ref["object"]["sha"]]
        st_c, commit = api("GET", f"/repos/{OWNER}/{REPO}/git/commits/{parents[0]}", token)
        if st_c == 200:
            base_tree = commit.get("tree", {}).get("sha")
    else:
        # 分支不存在：若仓库为空，先塞一个 README（避免 blobs 409）
        st_r, repo = api("GET", f"/repos/{OWNER}/{REPO}", token)
        if st_r == 200 and repo.get("size", 0) == 0:
            print("  仓库为空，先用 Contents API 初始化 README ...")
            api("PUT", f"/repos/{OWNER}/{REPO}/contents/README.md", token, {
                "message": "chore: init repository",
                "content": base64.b64encode(
                    "# 三角带行业资讯\n\n初始化仓库。\n".encode("utf-8")
                ).decode("ascii"),
                "branch": branch,
            })
            api("POST", f"/repos/{OWNER}/{REPO}/branches", token, {"name": branch, "from": "main"}) \
                if branch != "main" else None
            st, ref = api("GET", f"/repos/{OWNER}/{REPO}/git/ref/heads/{branch}", token)
            if st == 200:
                parents = [ref["object"]["sha"]]

    # 2) 上传 blobs
    entries = []
    total = len(file_paths)
    for i, full in enumerate(file_paths, 1):
        rel = os.path.relpath(full, base_dir).replace("\\", "/")
        with open(full, "rb") as f:
            content = f.read()
        st, blob = api("POST", f"/repos/{OWNER}/{REPO}/git/blobs", token, {
            "content": base64.b64encode(content).decode("ascii"),
            "encoding": "base64",
        })
        if st not in (200, 201):
            print(f"  ✗ blob 上传失败 {rel}: {st} {blob}")
            return False
        entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        if i % 10 == 0 or i == total:
            print(f"    blobs {i}/{total}")

    # 3) 建 tree（不带 base_tree，保证是完整快照，避免残留旧文件）
    tree_body = {"tree": entries}
    st, tree = api("POST", f"/repos/{OWNER}/{REPO}/git/trees", token, tree_body)
    if st not in (200, 201):
        print(f"  ✗ tree 创建失败: {st} {tree}")
        return False

    # 4) 建 commit
    st, commit = api("POST", f"/repos/{OWNER}/{REPO}/git/commits", token, {
        "message": message,
        "tree": tree["sha"],
        "parents": parents,
    })
    if st not in (200, 201):
        print(f"  ✗ commit 创建失败: {st} {commit}")
        return False

    # 5) 更新 / 创建 ref
    if parents:
        st, res = api("PATCH", f"/repos/{OWNER}/{REPO}/git/refs/heads/{branch}", token,
                      {"sha": commit["sha"], "force": True})
        if st not in (200, 201):
            print(f"  ✗ ref 更新失败: {st} {res}")
            return False
    else:
        st, res = api("POST", f"/repos/{OWNER}/{REPO}/git/refs", token,
                      {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
        if st not in (200, 201):
            print(f"  ✗ ref 创建失败: {st} {res}")
            return False

    print(f"  ✓ {branch} <- {commit['sha'][:8]}  ({total} 个文件)")
    return True


# ---------------------------------------------------------------- Pages

def setup_pages(token):
    st, info = api("GET", f"/repos/{OWNER}/{REPO}/pages", token)
    body = {"source": {"branch": PUB_BRANCH, "path": "/"}}
    if st == 200:
        st2, res = api("PUT", f"/repos/{OWNER}/{REPO}/pages", token, body)
        act = "更新"
    else:
        st2, res = api("POST", f"/repos/{OWNER}/{REPO}/pages", token, body)
        act = "启用"
    if st2 in (200, 201, 204):
        print(f"  ✓ Pages {act}成功（源：{PUB_BRANCH}）")
    else:
        print(f"  ! Pages {act}返回 {st2}：{res}")

    # 绑定自定义域名（必须在文件名/内容上与仓库 CNAME 一致）
    st3, res3 = api("PUT", f"/repos/{OWNER}/{REPO}/pages", token, {"cname": DOMAIN})
    if st3 in (200, 201, 204):
        print(f"  ✓ 自定义域名已绑定：{DOMAIN}")
    else:
        print(f"  ! 绑定域名返回 {st3}：{res3}")
        print("    可手动在 Settings → Pages → Custom domain 填 " + DOMAIN)


# ---------------------------------------------------------------- 主流程

def main():
    ap = argparse.ArgumentParser(description="发布三角带行业资讯站到 GitHub")
    ap.add_argument("--source-only", action="store_true", help="仅推送源码到 main")
    ap.add_argument("--source", action="store_true", help="同上（别名）")
    ap.add_argument("--pages", action="store_true", help="尝试启用 Pages 并绑定域名")
    args = ap.parse_args()

    token = get_token()
    if not token:
        print("✗ 未找到 GitHub 凭据。请设置 GITHUB_TOKEN，或在 ~/.git-credentials 写入：")
        print("    https://<用户名>:<TOKEN>@github.com")
        sys.exit(1)

    st, me = api("GET", "/user", token)
    if st != 200:
        print(f"✗ 凭据校验失败（{st}）：{me}")
        sys.exit(1)
    print(f"凭据校验通过：{me.get('login')}")
    print()

    src_files = collect_src()
    pub_files = collect_pub()

    print(f"[1] 推送源码到 {SRC_BRANCH}（{len(src_files)} 个文件）")
    if not push(token, SRC_BRANCH, src_files, ROOT, "feat: 三角带行业资讯站（静态站源码 + 构建脚本）"):
        sys.exit(1)

    skip_pub = args.source_only or args.source
    if skip_pub:
        print("\n(跳过构建产物推送)")
    else:
        if not pub_files:
            print("✗ public/ 为空，请先运行 python build.py")
            sys.exit(1)

        print(f"\n[2] 推送构建产物到 {PUB_BRANCH}（{len(pub_files)} 个文件）")
        if not push(token, PUB_BRANCH, pub_files, PUB, "build: 发布站点构建产物"):
            sys.exit(1)

    if args.pages:
        print(f"\n[3] 配置 GitHub Pages")
        setup_pages(token)

    if skip_pub and not args.pages:
        print("\n完成（仅源码）。")
        return

    print()
    print("=" * 62)
    print("  发布完成")
    print(f"    源码分支 : {SRC_BRANCH}")
    print(f"    发布分支 : {PUB_BRANCH}")
    print(f"    自定义域名: {DOMAIN}")
    print()
    print("  后续：")
    print("    1) 仓库 Settings → Pages 确认 Source 为 gh-pages / (root)")
    print(f"    2) Custom domain 填 {DOMAIN}（填中文会报错）")
    print("    3) DNS 添加 4 条 A 记录指向 185.199.108~111.153")
    print("    4) DNS 生效后勾选 Enforce HTTPS")
    print("=" * 62)


if __name__ == "__main__":
    main()
