#!/usr/bin/env python3
"""Generate a Markdown digest from the local WeChat RSS feed."""

from __future__ import annotations

import argparse
import html
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path


DEFAULT_RSS_URL = "http://localhost:5050/api/rss/all?limit=30"
DEFAULT_OUTPUT_DIR = Path("/Users/a123/Downloads/收藏自动更新/outputs")
LOCAL_TZ = timezone(timedelta(hours=8))


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


@dataclass
class RssItem:
    title: str
    author: str
    link: str
    published: datetime | None
    summary: str
    full_text: str
    score: int


def fetch_text(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 RSS Digest/1.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean_title(title: str, author: str) -> str:
    title = html.unescape(title or "").strip()
    if author:
        title = re.sub(rf"^\[{re.escape(author)}\]\s*", "", title)
    return title


def html_to_text(raw_html: str) -> str:
    parser = TextExtractor()
    parser.feed(html.unescape(raw_html or ""))
    return parser.text()


def clean_article_text(description: str, stop_at_footer: bool = True) -> str:
    text = html_to_text(description)
    stop_markers = ("往期推荐", "联系我们", "author:", "点击阅读")
    lines = []
    for raw_line in text.splitlines():
        line = re.sub(r"\s+", " ", raw_line).strip()
        if not line:
            continue
        if stop_at_footer and any(marker in line for marker in stop_markers):
            break
        if line in {"●", "01", "02", "03", "04"}:
            continue
        if "点击蓝字" in line or "关注我们" in line:
            continue
        lines.append(line)
    return "\n\n".join(lines).strip()


def compact_summary(description: str, max_chars: int = 220) -> str:
    summary = re.sub(r"\s+", " ", clean_article_text(description)).strip()
    if len(summary) > max_chars:
        summary = summary[: max_chars - 1].rstrip() + "..."
    return summary or "待补充"


def parse_pub_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(LOCAL_TZ)


def score_item(title: str, summary: str) -> int:
    text = f"{title} {summary}".lower()
    keywords = {
        "openai": 4,
        "ai": 2,
        "财报": 3,
        "政治局": 4,
        "宏观": 3,
        "美股": 3,
        "高盛": 2,
        "利率": 3,
        "关税": 3,
        "地产": 2,
        "储能": 2,
        "云": 2,
        "aws": 2,
        "meta": 2,
        "谷歌": 2,
        "微软": 2,
        "亚马逊": 2,
    }
    return sum(weight for keyword, weight in keywords.items() if keyword in text)


def parse_items(xml_text: str) -> list[RssItem]:
    root = ET.fromstring(xml_text)
    items = []
    for item in root.findall("./channel/item"):
        author = (item.findtext("author") or "").strip()
        raw_title = item.findtext("title") or ""
        title = clean_title(raw_title, author)
        link = (item.findtext("link") or "").strip()
        published = parse_pub_date(item.findtext("pubDate") or "")
        description = item.findtext("description") or ""
        summary = compact_summary(description)
        full_text = clean_article_text(description)
        items.append(
            RssItem(
                title=title,
                author=author or "未知来源",
                link=link,
                published=published,
                summary=summary,
                full_text=full_text,
                score=score_item(title, summary),
            )
        )
    items.sort(key=lambda x: x.published or datetime.min.replace(tzinfo=LOCAL_TZ), reverse=True)
    return items


def item_time(item: RssItem) -> str:
    if not item.published:
        return "时间未知"
    return item.published.strftime("%Y-%m-%d %H:%M")


def render_digest(items: list[RssItem], source_url: str, full_text: bool = False) -> str:
    now = datetime.now(LOCAL_TZ)
    grouped: dict[str, list[RssItem]] = defaultdict(list)
    for item in items:
        grouped[item.author].append(item)

    highlights = sorted(items, key=lambda x: (x.score, x.published or datetime.min.replace(tzinfo=LOCAL_TZ)), reverse=True)[:5]

    lines = [
        f"# 微信公众号每日素材包 - {now.strftime('%Y-%m-%d')}",
        "",
        f"- 生成时间：{now.strftime('%Y-%m-%d %H:%M')}",
        f"- 来源：{source_url}",
        f"- 文章数：{len(items)}",
        f"- 输出模式：{'全文版' if full_text else '摘要版'}",
        "",
        "## 值得优先看",
    ]

    if highlights:
        for item in highlights:
            lines.append(f"- [{item.author}] [{item.title}]({item.link})")
    else:
        lines.append("- 暂无")

    for author in sorted(grouped):
        lines.extend(["", f"## {author}"])
        for item in grouped[author]:
            lines.extend(
                [
                    f"### [{item.title}]({item.link})",
                    f"- 时间：{item_time(item)}",
                    f"- 摘要：{item.summary}",
                    "",
                ]
            )
            if full_text:
                lines.extend(
                    [
                        "#### 原文",
                        "",
                        item.full_text or "待补充",
                        "",
                    ]
                )

    return "\n".join(lines).rstrip() + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a Markdown digest from local WeChat RSS.")
    parser.add_argument("--url", default=DEFAULT_RSS_URL, help="RSS URL to read.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for Markdown output.")
    parser.add_argument("--output", default="", help="Optional explicit output file path.")
    parser.add_argument("--full-text", action="store_true", help="Include cleaned full article text.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    xml_text = fetch_text(args.url)
    items = parse_items(xml_text)
    if not items:
        print("No RSS items found.", file=sys.stderr)
        return 1

    digest = render_digest(items, args.url, full_text=args.full_text)
    default_prefix = "wechat-fulltext" if args.full_text else "wechat-digest"
    output_path = Path(args.output) if args.output else Path(args.output_dir) / f"{default_prefix}-{datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')}.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(digest, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
