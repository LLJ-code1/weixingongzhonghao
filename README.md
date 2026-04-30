# weixingongzhonghao

本仓库用于记录和辅助运行“微信公众号文章入库 -> RSS 输出 -> Markdown 整理”的本地流程。

当前已跑通的是手动流程：

- 使用 `wechat-query-skill` / `wechat-download-api` 登录公众号后台
- 手动触发公众号文章入库
- 通过本地 RSS API 查看文章
- 用脚本生成 Markdown 摘要、全文或新增清单

说明：本仓库只保存本地流程说明和辅助脚本，不保存克隆下来的原始 `wechat-query-skill` 仓库及其运行数据。

详细流程见：

[docs/微信RSS手动流程记录.md](docs/微信RSS手动流程记录.md)

## 常用入口

本地 RSS 页面：

```text
http://localhost:5050/rss.html
```

全量 RSS API：

```text
http://localhost:5050/api/rss/all
```

手动触发更新：

```bash
curl -s -X POST http://localhost:5050/api/rss/poll
```

## 常用脚本

生成摘要版素材包：

```bash
python3 scripts/wechat_rss_digest.py
```

生成全文版素材包：

```bash
python3 scripts/wechat_rss_digest.py --full-text
```

生成新增差异清单：

```bash
python3 scripts/wechat_rss_new.py
```

查看输出：

```bash
open outputs
```

## 当前状态

- 本机服务端口：`5050`
- 当前流程：手动刷新为主
- 当前新增判断：基于文章链接和 `state/seen-links.txt`
- 当前输出：Markdown 文件，默认放在 `outputs/`
- 后续自动化另行设计，本文档先不展开

## 注意

- `outputs/`、`state/`、数据库和登录状态属于运行数据，不建议同步到 Git。
- 若要判断“新增”，必须先有更新前基线，再触发更新，再运行新增差异脚本。
- 如果是先更新、后建基线，本次新增会被当作已见过，无法用链接基线倒推差异。
