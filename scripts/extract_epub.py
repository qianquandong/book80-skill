#!/usr/bin/env python3
"""Extract EPUB spine documents into ordered, readable text files."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import unquote
from xml.etree import ElementTree as ET


class TextExtractor(HTMLParser):
    BLOCK_TAGS = {
        "address", "article", "aside", "blockquote", "br", "div", "figcaption",
        "figure", "footer", "h1", "h2", "h3", "h4", "h5", "h6", "header",
        "hr", "li", "main", "nav", "ol", "p", "pre", "section", "table",
        "td", "th", "tr", "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.ignored_depth = 0
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "svg"}:
            self.ignored_depth += 1
        if tag == "title":
            self.in_title = True
        if tag in self.BLOCK_TAGS and not self.ignored_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "svg"} and self.ignored_depth:
            self.ignored_depth -= 1
        if tag == "title":
            self.in_title = False
        if tag in self.BLOCK_TAGS and not self.ignored_depth:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        if self.in_title:
            self.title_parts.append(data)
            return
        self.parts.append(data)

    def text(self) -> str:
        value = html.unescape("".join(self.parts)).replace("\u00a0", " ")
        value = re.sub(r"[ \t]+", " ", value)
        value = re.sub(r" *\n *", "\n", value)
        value = re.sub(r"\n{3,}", "\n\n", value)
        return value.strip()

    def title(self) -> str:
        return re.sub(r"\s+", " ", "".join(self.title_parts)).strip()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def find_child(root: ET.Element, name: str) -> ET.Element | None:
    return next((node for node in root.iter() if local_name(node.tag) == name), None)


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-._")
    return value[:80] or "section"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("epub", type=Path, help="Path to a DRM-free EPUB file")
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.epub.is_file():
        print(f"error: file not found: {args.epub}", file=sys.stderr)
        return 2

    args.output_dir.mkdir(parents=True, exist_ok=True)

    try:
        archive = zipfile.ZipFile(args.epub)
    except zipfile.BadZipFile:
        print("error: input is not a valid EPUB/ZIP file", file=sys.stderr)
        return 2

    with archive:
        try:
            container = ET.fromstring(archive.read("META-INF/container.xml"))
            rootfile = next(
                node.attrib["full-path"]
                for node in container.iter()
                if local_name(node.tag) == "rootfile"
            )
            package = ET.fromstring(archive.read(rootfile))
        except (KeyError, ET.ParseError, StopIteration) as exc:
            print(f"error: malformed EPUB package: {exc}", file=sys.stderr)
            return 2

        manifest_node = find_child(package, "manifest")
        spine_node = find_child(package, "spine")
        if manifest_node is None or spine_node is None:
            print("error: EPUB has no readable manifest/spine", file=sys.stderr)
            return 2

        items = {
            node.attrib.get("id", ""): node.attrib
            for node in manifest_node
            if local_name(node.tag) == "item"
        }
        spine_ids = [
            node.attrib.get("idref", "")
            for node in spine_node
            if local_name(node.tag) == "itemref" and node.attrib.get("linear", "yes") != "no"
        ]

        package_dir = PurePosixPath(rootfile).parent
        records: list[dict[str, object]] = []
        for index, item_id in enumerate(spine_ids, start=1):
            item = items.get(item_id)
            if not item or "href" not in item:
                continue
            source_path = str(package_dir / PurePosixPath(unquote(item["href"])))
            try:
                raw = archive.read(source_path).decode("utf-8", errors="replace")
            except KeyError:
                continue
            extractor = TextExtractor()
            extractor.feed(raw)
            text = extractor.text()
            if not text:
                continue
            title = extractor.title() or PurePosixPath(source_path).stem
            filename = f"{index:03d}-{safe_name(title)}.txt"
            content = f"SOURCE: EPUB spine {index}, {source_path}\nTITLE: {title}\n\n{text}\n"
            (args.output_dir / filename).write_text(content, encoding="utf-8")
            records.append(
                {
                    "spine_index": index,
                    "id": item_id,
                    "title": title,
                    "source_path": source_path,
                    "output_file": filename,
                    "characters": len(text),
                }
            )

    manifest = {
        "source_file": str(args.epub.resolve()),
        "sections_extracted": len(records),
        "sections": records,
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"extracted {len(records)} sections to {args.output_dir}")
    return 0 if records else 1


if __name__ == "__main__":
    raise SystemExit(main())
