#!/usr/bin/env python3
"""Report newly seen WeChat RSS articles since the last run."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from wechat_rss_digest import (  # noqa: E402
    DEFAULT_OUTPUT_DIR,
    LOCAL_TZ,
    RssItem,
    fetch_text,
    item_time,
    parse_items,
)


DEFAULT_RSS_URL = "http://localhost:5050/api/rss/all?limit=100"
DEFAULT_STATE_FILE = Path("/Users/a123/Downloads/收藏自动更新/state/seen-links.txt")


def read_seen_links(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()}


def write_seen_links(path: Path, links: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(sorted(links)) + "\n", encoding="utf-8")


def item_link(item: RssItem) -> str:
    return item.link.strip()


def render_new_items(
    items: list[RssItem],
    new_items: list[RssItem],
    source_url: str,
    state_file: Path,
    initialized_baseline: bool,
    full_text: bool,
) -> str:
    now = datetime.now(LOCAL_TZ)
    grouped: dict[str, list[RssItem]] = defaultdict(list)
    for item in new_items:
        grouped[item.author].append(item)

    lines = [
        f"# 微信公众号新增文章 - {now.strftime('%Y-%m-%d %H:%M')}",
        "",
        f"- 来源：{source_url}",
        f"- 当前 RSS 文章数：{len(items)}",
        f"- 本次新增：{len(new_items)}",
        f"- 已读基线：{state_file}",
        f"- 输出模式：{'全文版' if full_text else '摘要版'}",
    ]

    if initialized_baseline:
        lines.extend(
            [
                "",
                "## 本次是第一次建立基线",
                "",
                "这次不把现有文章算作新增。之后你更新入库后再运行本脚本，就会只列出新增文章。",
            ]
        )
        return "\n".join(lines).rstrip() + "\n"

    if not new_items:
        lines.extend(["", "## 无新增", "", "当前 RSS 里的文章都已经在基线中。"])
        return "\n".join(lines).rstrip() + "\n"

    lines.extend(["", "## 新增清单"])
    for author in sorted(grouped):
        lines.extend(["", f"### {author}"])
        for item in grouped[author]:
            lines.extend(
                [
                    f"- [{item.title}]({item.link})",
                    f"  - 时间：{item_time(item)}",
                    f"  - 摘要：{item.summary}",
                ]
            )
            if full_text:
                lines.extend(["", item.full_text or "待补充", ""])

    return "\n".join(lines).rstrip() + "\n"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report newly seen WeChat RSS articles.")
    parser.add_argument("--url", default=DEFAULT_RSS_URL, help="RSS URL to read.")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE), help="File that stores seen article links.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for Markdown output.")
    parser.add_argument("--output", default="", help="Optional explicit output file path.")
    parser.add_argument("--dry-run", action="store_true", help="Do not update the seen-link state file.")
    parser.add_argument(
        "--include-first-run",
        action="store_true",
        help="If the state file does not exist, report all current RSS items as new.",
    )
    parser.add_argument("--full-text", action="store_true", help="Include cleaned full article text for new items.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    state_file = Path(args.state_file)
    output_dir = Path(args.output_dir)

    xml_text = fetch_text(args.url)
    items = parse_items(xml_text)
    if not items:
        print("No RSS items found.", file=sys.stderr)
        return 1

    state_exists = state_file.exists()
    seen_links = read_seen_links(state_file)
    current_links = {item_link(item) for item in items if item_link(item)}

    initialized_baseline = not state_exists and not args.include_first_run
    if initialized_baseline:
        new_items: list[RssItem] = []
    else:
        new_items = [item for item in items if item_link(item) and item_link(item) not in seen_links]

    report = render_new_items(
        items=items,
        new_items=new_items,
        source_url=args.url,
        state_file=state_file,
        initialized_baseline=initialized_baseline,
        full_text=args.full_text,
    )

    output_path = (
        Path(args.output)
        if args.output
        else output_dir / f"wechat-new-{datetime.now(LOCAL_TZ).strftime('%Y-%m-%d-%H%M%S')}.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    if not args.dry_run:
        write_seen_links(state_file, seen_links | current_links)

    print(output_path)
    print(f"new={len(new_items)} total={len(items)} state_updated={not args.dry_run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
