# 三角带.com 站点部署说明

## 站点信息

- 域名：三角带.com（punycode：`xn--ehqs60bj46a.com`）
- 仓库：https://github.com/mfujun2025/sanjiaodai
- 生成器：Hugo v0.165+（extended）
- 输出目录：`public/`
- 部署目标：GitHub Pages

## 本地构建

```bash
cd sanjiaodai-site
hugo --minify        # 输出到 public/
hugo server          # 本地预览 http://localhost:1313/
```

## 目录结构

```
sanjiaodai-site/
├── hugo.yaml                  # 站点配置（baseURL / 导航 / 参数）
├── assets/css/main.css        # 样式（构建时压缩 + 指纹）
├── layouts/
│   ├── _default/baseof.html   # 基础模板（SEO meta / OG / Schema）
│   ├── _default/single.html   # 文章页模板（含目录 / FAQ / 面包屑）
│   ├── _default/list.html     # 栏目列表模板
│   ├── index.html             # 首页
│   └── partials/              # header / footer
├── content/
│   ├── guide/sanjiaodai-xinghao-guige.md   # 首篇 Pillar 长文
│   ├── guide/_index.md        # 知识指南栏目
│   ├── models/_index.md       # 型号对照表
│   ├── selector/_index.md     # 选型计算器
│   ├── install/_index.md      # 安装步骤与松紧度
│   ├── faults/_index.md       # 故障排查
│   ├── products/_index.md     # 产品中心
│   └── about/_index.md        # 关于本站
└── static/CNAME               # GitHub Pages 自定义域名
```

## 部署到 GitHub Pages

### 方式一：手动推送 public/

```bash
cd sanjiaodai-site
hugo --minify
cd public
git init
git branch -M gh-pages
git add -A
git commit -m "deploy: 三角带.com 站点上线"
git remote add origin https://github.com/mfujun2025/sanjiaodai.git
git push -u origin gh-pages
```

然后在仓库 Settings → Pages 里把 Source 设为 `gh-pages` 分支。

### 方式二：GitHub Actions 自动构建（推荐）

在仓库根目录建 `.github/workflows/hugo.yml`，push 到 `main` 时自动构建并发布。需在源文件仓库（含 hugo.yaml / layouts / content）上启用。

> 注意：本机 `git push` 可能被环境拦截（Watt Toolkit 干扰）。若 push 失败，可用 GitHub Data API 逐文件上传（参考既有 `github-push-via-data-api` 技能）。

## 中文域名注意事项

1. **CNAME 用 punycode**：`xn--ehqs60bj46a.com`，不要写中文。
2. **baseURL 用 punycode**：`https://xn--ehqs60bj46a.com/`，避免 canonical/sitemap 出现中文导致编码问题。
3. **DNS 解析**：到域名服务商给 `xn--ehqs60bj46a.com` 添加 CNAME 记录指向 `mfujun2025.github.io`，或添加 A 记录指向 GitHub Pages IP。
4. **强制 HTTPS**：域名生效后在 Pages 设置里勾选 Enforce HTTPS。

## 上线后必做

- [ ] 在百度搜索资源平台验证站点并提交 `sitemap.xml`
- [ ] 提交首页 URL 加速收录
- [ ] 检查 `robots.txt` 允许抓取
- [ ] 移动端实测（模板断点 820px）
