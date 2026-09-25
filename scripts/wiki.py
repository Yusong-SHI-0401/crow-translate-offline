#!/usr/bin/env python3
"""Generate GitHub Wiki pages from the versioned docs source."""
import argparse
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("destination", type=Path, help="Empty directory for generated wiki pages")
args = parser.parse_args()
if args.destination.exists() and any(args.destination.iterdir()):
    parser.error("Destination must be empty; back up existing wiki files first")
args.destination.mkdir(parents=True, exist_ok=True)
pages = sorted((root / "docs").glob("*.md"))
for page in pages:
    text = re.sub(r"\]\(([A-Za-z-]+)\.md\)", r"](\1)", page.read_text())
    (args.destination / page.name).write_text(text)
(args.destination / "_Sidebar.md").write_text("\n".join(
    f"- [{page.read_text().splitlines()[0].removeprefix('# ')}]({page.stem})" for page in pages) + "\n")
print(f"Generated {len(pages)} pages and sidebar at {args.destination}")
