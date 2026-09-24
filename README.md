# 三角带行业资讯（三角带.com）

面向**机械传动行业采购与技术人员**的三角带（V 带）行业资讯站。纯静态站点，无后端，可直接部署到 GitHub Pages。

- **中文域名**：三角带.com
- **Punycode**：`xn--ehqs60bj46a.com`
- **线上地址**：https://xn--ehqs60bj46a.com
- **仓库**：https://github.com/mfujun2025/sanjiaodai

---

## 一、站点结构

```
/                       首页：资讯推荐 + 栏目导航 + 速查入口
/basics/                三角带基础知识（结构、材质、三尺寸）
/models/                型号规格速查（命名规则、普通V带 vs 窄V带）
/guide/                 选型与安装维护（选型计算、安装张紧、失效分析）
/news/                  行业动态（趋势观察、采购实务）
/faq/                   常见问题（高频问答、点检清单）
/category/<栏目>/        栏目聚合页
/news/                  全部内容（按年份分组）
/specs/                 型号规格速查表（9 张表，可打印）
/search/                站内搜索（前端索引匹配）
/sitemap/               网站地图（HTML 版，含全部页面与文章）
/about/                 关于本站（定位、内容原则、免责声明）
/sitemap.xml            搜索引擎网站地图
/robots.txt             爬虫规则
/404.html               自定义 404 页
/CNAME                  GitHub Pages 自定义域名
```

### 栏目定义

| slug | 栏目名 | 内容 |
|---|---|---|
| `basics` | 三角带基础知识 | 结构分层、胶料与骨架、顶宽/节宽/高度辨析、工作原理 |
| `models` | 型号规格速查 | 命名规则、普通 V 带 vs 窄 V 带对比 |
| `guide` | 选型与安装维护 | 选型计算、安装张紧、失效形式排查 |
| `news` | 行业动态 | 行业趋势、采购实务 |
| `faq` | 常见问题 | 高频问答、点检清单与更换决策 |

---

## 二、目录说明

```
sanjiaodai/
├── site.json            站点元信息（名称、域名、导航、页脚）
├── categories.json      栏目定义（slug / 名称 / 描述 / 关键词）
├── specs.json           速查表数据（9 张表，JSON 驱动）
├── build.py             构建脚本：所有输入 → public/
├── check.py             构建产物自检（内链、SEO、sitemap 一致性等）
├── deploy.py            发布脚本（GitHub Git Data API）
├── content/             文章源文件（Markdown + front matter）
│   ├── basics/          按栏目分目录，目录名 = 栏目 slug
│   ├── models/
│   ├── guide/
│   ├── news/
│   ├── faq/
│   └── about.md         关于页
├── templates/           HTML 模板（{{TOKEN}} 占位符）
│   ├── layout.html      全站骨架（head / 导航 / 页脚）
│   ├── index.html       首页
│   ├── list.html        列表页（栏目页 / 全部内容）
│   ├── article.html     文章详情页
│   ├── specs.html       速查表页
│   ├── search.html      搜索页
│   ├── sitemap.html     网站地图页
│   └── 404.html         404 页
├── static/              静态资源，递归平铺复制到站点根
│   └── assets/          style.css / main.js / favicon.svg
└── public/              构建产物（可直接部署，不手工编辑）
```

**关键约定**：`public/` 是构建产物，**不要手工往里放文件**——所有资源都放 `static/`，构建时递归平铺复制；域名与 `.nojekyll` 由 `build.py` 固定产出，避免部署时被覆盖式提交抹掉。

---

## 三、本地预览

### 1. 环境准备

需要 Python 3.10+ 与 `markdown` 库：

```bash
pip install markdown
```

> 若本机使用 WorkBuddy 隔离环境，解释器路径为
> `C:/Users/<user>/.workbuddy/binaries/python/envs/default/Scripts/python.exe`

### 2. 构建

```bash
cd sanjiaodai
python build.py
```

输出示例：

```
==============================================================
  站点：三角带行业资讯  (三角带.com / xn--ehqs60bj46a.com)
==============================================================
  文章数        : 12
  栏目数        : 5
  HTML 页面数   : 25
  网站地图声明  : 22 条 URL（页面 + 文章）
  搜索索引条目  : 12 篇
  速查表格      : 9 张 / 53 行数据
  静态资源      : 3 个 + CNAME/.nojekyll
  输出目录      : public/
==============================================================
```

### 3. 自检（推荐每次构建后执行）

```bash
python check.py
```

检查 9 类问题：占位符残留、内链有效性、sitemap 与文章数一致性、搜索索引完整性、关键文件存在性、SEO 基础项（title / description / canonical）、根目录调试文件残留等。**全部通过时退出码为 0**。

### 4. 起本地服务预览

```bash
python -m http.server 8912 --directory public
```

然后浏览器打开 http://127.0.0.1:8912/

> **端口提示**：本机 80 端口可能被其他软件占用，`8000` / `8080` / `8791` 也常有别的服务遗留。**建议从 `8899` 往上挑**，起完先访问一次确认返回的是本站页面。

---

## 四、如何新增一篇文章

1. 在对应栏目目录下新建 `.md` 文件，例如 `content/guide/sanjiaodai-zhangjin-zhenduan.md`
2. 写 front matter（**必填 `title` / `slug` / `category` / `date` / `desc`**）：

```markdown
---
title: 三角带张紧力诊断：三种现场方法对比
slug: sanjiaodai-zhangjin-zhenduan
category: guide
date: 2026-10-01
desc: 手感法、挠度法、张力计法各自的适用场景与操作要点，附判定数值与常见误判。
keywords: 三角带张紧力,张紧力检测,挠度法,张力计
featured: false
---

## 一、正文标题

正文内容……
```

3. 重新构建并自检：

```bash
python build.py && python check.py
```

**会自动完成的事**：进搜索索引、进 sitemap.xml、进 HTML 网站地图、进所在栏目页、进首页「最新」区（按日期倒序）、生成面包屑与 JSON-LD 结构化数据、自动生成右侧目录导航。

**注意**：
- `slug` 决定 URL（`/<category>/<slug>/`），一旦发布**不要再改**，否则旧链接会 404
- `date` 用 `YYYY-MM-DD` 格式，首页与列表按它倒序排列
- `desc` 同时用于列表卡片和 meta description，值得单独写好（建议 60~80 全角字）
- `featured: true` 的文章会进首页「重点推荐」（最多取 4 篇）
- 标题建议控制在 **30 全角字以内**（`check.py` 会对超长标题给出提示）

新增一个**栏目**：改 `categories.json` 加一条，在 `content/` 下建同名目录，在 `site.json` 的 `nav` 里加导航项，重新构建即可。

修改**速查表**：直接编辑 `specs.json`（表格数据全在 JSON 里，不用碰模板）。

---

## 五、发布到 GitHub Pages

### 方式一：用发布脚本（推荐）

`deploy.py` 走 **GitHub Git Data API**（blobs → tree → commit → ref），**不依赖 `git push`**——在本机安装有网络加速工具的环境下，`git push` 会被 SIGTERM 拦截，API 方式更可靠。

```bash
python deploy.py --source          # 仅推送源码到 main 分支
python deploy.py                   # 推送源码到 main + 构建产物到 gh-pages
```

凭据来源（按顺序读取，取到即用）：

1. 环境变量 `GITHUB_TOKEN`
2. `~/.git-credentials` 中的 GitHub 条目（格式 `https://<user>:<token>@github.com`）

**Token 需要的权限**：仓库为 **Contents: Read and write**；若要脚本自动启用 Pages / 绑定域名，还需 **Pages: Read and write**。

### 方式二：手动 git（本机可能受阻）

```bash
git init
git remote add origin https://github.com/mfujun2025/sanjiaodai.git
git add .
git commit -m "feat: 三角带行业资讯站"
git push -u origin main
```

> 本机装有网络加速工具时会拦截 `git push`。若命令无输出即被终止，改用上面的 API 方式。

### 发布分支约定

| 分支 | 内容 | 用途 |
|---|---|---|
| `main` | 源码（`content/` / `templates/` / `static/` / `*.py` / `*.json`） | 二次开发与内容维护 |
| `gh-pages` | `public/` 的构建产物（**站点根目录**） | GitHub Pages 发布源 |

---

## 六、域名与 DNS 配置

### 1. 域名信息

| 项目 | 值 |
|---|---|
| 中文域名 | 三角带.com |
| Punycode | `xn--ehqs60bj46a.com` |

> **重要**：GitHub Pages 的 Custom domain 设置**必须填 Punycode**（`xn--ehqs60bj46a.com`），**填中文会报错**。仓库根目录的 `CNAME` 文件内容也是 Punycode 形式。

### 2. GitHub Pages 设置

1. 打开仓库 → **Settings** → **Pages**
2. **Source** 选 `Deploy from a branch`
3. **Branch** 选 `gh-pages`，目录选 `/ (root)`，保存
4. **Custom domain** 填 `xn--ehqs60bj46a.com`，点 Save
5. 等 DNS 生效后，勾选 **Enforce HTTPS**

> 证书签发前 `Enforce HTTPS` 是灰的，属正常。DNS 生效后 GitHub 会自动签发证书（通常 15 分钟 ~ 24 小时），签完再勾即可。

### 3. DNS 解析配置（关键：裸域名用 A 记录，不是 CNAME）

**三角带.com 是裸域名（apex domain，无 www 前缀）**，国内 DNS 服务商对 apex 域名的 CNAME 支持普遍不完整，配了大概率不生效。**正确做法是添加 4 条 A 记录**：

| 主机记录 | 记录类型 | 记录值 |
|---|---|---|
| `@` | A | `185.199.108.153` |
| `@` | A | `185.199.109.153` |
| `@` | A | `185.199.110.153` |
| `@` | A | `185.199.111.153` |

可选 IPv6（AAAA 记录）：

| 主机记录 | 记录类型 | 记录值 |
|---|---|---|
| `@` | AAAA | `2606:50c0:8000::153` |
| `@` | AAAA | `2606:50c0:8001::153` |
| `@` | AAAA | `2606:50c0:8002::153` |
| `@` | AAAA | `2606:50c0:8003::153` |

**若要同时用 www 子域名**（子域名可以用 CNAME）：

| 主机记录 | 记录类型 | 记录值 |
|---|---|---|
| `www` | CNAME | `mfujun2025.github.io` |

> 若 DNS 服务商支持 **ALIAS / ANAME** 记录，也可只加一条 `@ → mfujun2025.github.io`，效果等同。

### 4. 验证 DNS 是否生效

```bash
# 查询 A 记录，应返回 185.199.108.153 ~ 185.199.111.153
nslookup -type=A xn--ehqs60bj46a.com 8.8.8.8

# 直接访问验证
curl -sI https://xn--ehqs60bj46a.com/ | head -3
```

> DNS 生效前，域名访问到的是**注册商停放广告页**——这不是站点没部署成功，等解析生效即可。

---

## 七、部署后验证清单

按顺序执行，每步的判定标准在右侧：

| # | 操作 | 判定标准 |
|---|---|---|
| 1 | `curl -sI https://xn--ehqs60bj46a.com/` | 返回 `HTTP/2 200` |
| 2 | `curl -s -o /dev/null -w '%{http_code}' https://xn--ehqs60bj46a.com/CNAME` | `200`，内容为 `xn--ehqs60bj46a.com` |
| 3 | 访问 `/sitemap.xml` | 返回 XML，`<loc>` 全是 `https://xn--ehqs60bj46a.com/...` |
| 4 | 访问 `/robots.txt` | 包含 `Sitemap: https://xn--ehqs60bj46a.com/sitemap.xml` |
| 5 | 访问一个**不存在的路径** | 显示自定义 404 页（不是 GitHub 默认页） |
| 6 | 访问 `/search/` 并搜索「选型」 | 出现结果列表与高亮 |
| 7 | 手机浏览器打开首页 | 导航折叠为「菜单」按钮，无横向滚动条 |
| 8 | 浏览器「查看源代码」搜 `{{` | 无结果（无占位符残留） |

> **绑定自定义域名后，`mfujun2025.github.io/sanjiaodai/` 会 301 跳转到自定义域名**——这是正常行为，不是故障。此时验证请一律打自定义域名。

---

## 八、内容原则

本站面向机械传动行业的技术与采购人员，**数值准确优先于内容丰富**：

1. **区分数据性质**：标准值 / 经验参考值 / 厂家数据分别标注，不混为一谈。正式设计必须以**现行国家标准**和**所采购厂家的技术文件**为准。
2. **不给不可核验的承诺**：给出判断方法与排查思路，不替代针对具体设备的核算。涉及起重、载人、防爆等安全相关传动，须由具备资质的工程师完成设计。
3. **厂商中立**：不评价、不推荐具体企业与品牌，不含商业推广内容。
4. **行业动态基于公开信息**：只做方向性梳理，不引用未公开数据，不构成投资或采购建议。
5. **每页保留免责声明**：见 `/about/`。

---

## 九、技术说明

| 项目 | 说明 |
|---|---|
| 技术栈 | 纯静态 HTML + CSS + 原生 JS，**零运行时依赖、零外部 CDN** |
| 构建 | Python + `markdown` 库，模板用 `{{TOKEN}}` + `str.replace` |
| URL 结构 | 目录式（`/news/`、`/guide/xxx/`），GitHub Pages 原生支持 |
| 响应式 | 移动优先，断点 900 / 768 / 420，含打印样式 |
| 无障碍 | skip-link、语义化标签、`aria-label`、键盘可达、`:focus-visible` 焦点样式 |
| SEO | canonical、Open Graph、JSON-LD（WebSite / Article / BreadcrumbList）、sitemap.xml + HTML 地图、语义化标题层级 |
| 搜索 | 前端加载 `search-index.json`，多关键词 AND 匹配 + 字段权重（标题 100 / 关键词 45 / 栏目 25 / 摘要 20 / 正文 8）+ 高亮 |
| 移动端导航 | CSS checkbox hack 折叠，**不依赖 JS** |
| 性能 | 单页 CSS + 单页 JS（约 8KB），无图片请求，首屏无阻塞资源 |

---

## 十、常见问题

**Q：本地打开 `public/index.html` 没有样式？**
A：用了根相对路径（`/assets/style.css`），必须通过 HTTP 服务访问。用 `python -m http.server` 起服务，不要双击打开文件。

**Q：`python build.py` 报 `ModuleNotFoundError: No module named 'markdown'`？**
A：装依赖 `pip install markdown`，或改用已安装该库的解释器（见「本地预览」节的路径说明）。

**Q：部署后站点打开是空白/404？**
A：依次检查：① Pages 的 Source 是否选了 `gh-pages` 分支的 `/ (root)`；② `gh-pages` 分支根目录是否有 `index.html`；③ 是否刚推送完还在部署（Pages 首次部署需要 1~3 分钟）。

**Q：改了样式线上没变化？**
A：浏览器或 CDN 缓存。强刷（Ctrl/Cmd + Shift + R）或用无痕窗口验证。

**Q：`check.py` 报「内链失效」怎么办？**
A：说明有链接指向不存在的页面。最常见的原因是改了文章的 `slug` 但没改引用它的地方，或删了文章但 `public/` 里有残留旧目录（构建是覆盖式写入，不清空输出目录，需手工删掉对应目录后重建）。

**Q：想换域名怎么办？**
A：改 `site.json` 的 `domain` / `domain_cn` / `base_url` 三项，重新构建部署，然后在 Pages 设置里改 Custom domain 并更新 DNS。

---

## 免责声明

本站内容为行业知识分享与技术经验整理，**仅供参考**。实际的设计、选型、采购、安装与维护作业，请依据现行国家标准与行业标准、设备制造厂家的技术文件与操作规程、以及所采购产品供应商提供的技术数据表。涉及安全的作业，请严格遵守所在单位的安全生产规程与作业许可制度。
