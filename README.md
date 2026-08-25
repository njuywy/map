# 炜煜之博客与通海铁路地图

项目使用 Hexo + Butterfly 主题搭建，并将“南通港通海港区至通州湾港区铁路专用线”交互式地图设置为网站首页。原博客文章列表保留在 `/blog/`。

## 快速开始

### 安装依赖
```bash
npm install
```

### 本地预览
```bash
hexo s
```
访问 http://localhost:4000

- 地图首页：http://localhost:4000
- 博客文章：http://localhost:4000/blog/

## 铁路地图

- 部署源文件位于 `source/` 根目录，由 Hexo 原样复制到网站根目录。
- 地图包含73个 CGCS2000 点位、离线卫星底图、本地 Leaflet 和天地图在线瓦片缓存。
- 点击任一点位可以查看并复制经纬度。
- 本地开发快照保存在 `archive/tonghai-railway-local-20260825/`，可独立运行和继续刷新坐标。

### 新建文章
```bash
hexo new "文章标题"
```

### 部署到 GitHub Pages
```bash
hexo d -g
```

## 目录结构
- `source/_posts/` - 文章存放位置
- `source/index.html` - 通海铁路交互地图首页
- `archive/tonghai-railway-local-20260825/` - 整合前的本地应用快照
- `themes/butterfly/` - 主题
- `docs/` - 生成的静态文件

## 部署配置

编辑 `_config.yml` 中的 deploy 部分：

```yaml
deploy:
  type: git
  repo: https://github.com/你的用户名/你的仓库名.git
  branch: gh-pages
```

需要先安装部署插件：
```bash
npm install hexo-deployer-git --save
```

## GitHub Pages 部署步骤

1. 创建 GitHub 仓库（如 `username.github.io`）
2. 推送博客代码到仓库
3. 启用 GitHub Pages（source: gh-pages 分支）
4. 访问 https://username.github.io

## Vercel 部署（推荐）

1. 注册 [Vercel](https://vercel.com)
2. 导入 GitHub 仓库
3. Vercel 自动检测 Hexo 并部署
4. 绑定自定义域名（可选）

---

*Powered by Hexo & Butterfly*
