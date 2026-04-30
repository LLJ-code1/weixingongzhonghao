# 微信 RSS 手动流程记录

## 目标

把已关注公众号的文章抓取到本地，并整理成可读的 Markdown 素材。

当前阶段只记录手动流程，不设计自动化。

## 当前链路

```text
公众号后台登录
-> wechat-download-api 抓取文章
-> 本地 SQLite 数据库
-> 本地 RSS API
-> Markdown 摘要 / 全文 / 新增清单
```

## 本地服务

服务目录：

```text
/Users/a123/Downloads/收藏自动更新/wechat-query-skill/services/wechat-download-api
```

本机访问端口：

```text
http://localhost:5050
```

常用页面：

```text
http://localhost:5050/rss.html
```

常用 API：

```text
http://localhost:5050/api/rss/all
http://localhost:5050/api/rss/all?limit=10
http://localhost:5050/api/rss/all?limit=100
```

手动触发更新：

```bash
curl -s -X POST http://localhost:5050/api/rss/poll
```

数据库位置：

```text
wechat-query-skill/services/wechat-download-api/data/rss.db
```

## 已验证能力

- 可以登录公众号后台账号。
- 可以读取已关注公众号列表。
- 可以手动触发文章入库。
- 可以通过 `http://localhost:5050/api/rss/all` 访问 RSS 内容。
- 数据库中包含文章标题、来源、链接、摘要、HTML 内容、清洗后的纯文本内容。
- 不是只有内容简述，部分文章已经能抓到原文。
- 可以生成摘要版 Markdown。
- 可以生成全文版 Markdown。
- 可以基于文章链接生成新增差异清单。

## 手动操作流程

### 1. 确认服务可用

打开：

```text
http://localhost:5050/rss.html
```

如果页面可以打开，说明本地服务在运行。

### 2. 手动更新入库

在页面上点击“立即轮询”，或用命令：

```bash
curl -s -X POST http://localhost:5050/api/rss/poll
```

### 3. 确认 RSS 有内容

打开：

```text
http://localhost:5050/api/rss/all?limit=10
```

如果能看到 XML 内容，说明 RSS 输出正常。

### 4. 生成摘要版素材

```bash
python3 scripts/wechat_rss_digest.py
```

默认输出：

```text
outputs/wechat-digest-YYYY-MM-DD.md
```

### 5. 生成全文版素材

```bash
python3 scripts/wechat_rss_digest.py --full-text
```

默认输出：

```text
outputs/wechat-fulltext-YYYY-MM-DD.md
```

### 6. 生成新增差异清单

```bash
python3 scripts/wechat_rss_new.py
```

默认输出：

```text
outputs/wechat-new-YYYY-MM-DD-HHMMSS.md
```

新增判断依据：

```text
state/seen-links.txt
```

## 新增差异的关键规则

新增差异不是按“页面最新”判断，而是按“是否已经在本地基线中出现过”判断。

正确顺序：

```text
先建立基线
-> 再更新入库
-> 再运行新增差异脚本
-> 得到新增文章
```

如果已经先更新了，再建立基线，那么刚刚更新进来的文章会被记录为“已见过”，不会再显示为新增。

这次遇到的例子：

```text
【中国银河宏观】中东局势如何影响4月PMI——2026年4月PMI分析
```

这篇文章实际已经在数据库中，且有原文内容，但因为基线是在更新之后建立的，所以不会出现在“新增”清单里。

## 当前最新内容的判断方式

如果只是想看当前库里最新文章，不要看新增脚本，而应该按发布时间倒序查看数据库或生成全量快照。

数据库查询方式：

```bash
sqlite3 wechat-query-skill/services/wechat-download-api/data/rss.db "SELECT title, author, link, datetime(publish_time, 'unixepoch', 'localtime') FROM articles ORDER BY publish_time DESC LIMIT 20;"
```

当前全量快照生成方式：

```bash
python3 scripts/wechat_rss_digest.py --url 'http://localhost:5050/api/rss/all?limit=100' --output outputs/wechat-digest-current-YYYY-MM-DD.md
```

## 当前已知问题

- 本机网络代理不能完全关闭，否则会影响连接。
- 代理状态会影响公众号登录和轮询稳定性。
- 当前电脑更适合作为手动验证环境，不适合作为长期无人值守环境。
- `api/rss/all` 是全量列表，不等于“今日新增”。
- `limit` 太小会漏掉更多历史文章，生成全量快照时建议使用 `limit=100` 或更高。
- 新增差异依赖基线文件，基线建立时机很重要。

## 文件边界

建议同步到 Git：

```text
README.md
docs/微信RSS手动流程记录.md
scripts/wechat_rss_digest.py
scripts/wechat_rss_new.py
.gitignore
```

不建议同步到 Git：

```text
outputs/
state/
wechat-query-skill/services/wechat-download-api/data/
wechat-query-skill/services/wechat-download-api/.env
scripts/__pycache__/
```

原因：

- `outputs/` 是每次运行生成的结果文件。
- `state/` 是本地已读基线，换设备后可能需要重新建立。
- `data/` 里包含数据库和运行状态。
- `.env` 可能包含本地配置。

## 后续待处理

- NAS / Docker 上长期运行方案。
- 定时刷新方式。
- 新增内容推送方式。
- 是否把新增 Markdown 自动进入 LifeOS。

这些属于后续自动化设计，本记录暂不展开。
