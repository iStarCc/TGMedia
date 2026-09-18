#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> None:
    version = sys.argv[1] if len(sys.argv) > 1 else json.loads(Path("version.json").read_text())["version"]
    data = json.loads(Path("version.json").read_text())
    entry = next((e for e in data.get("changelog", []) if e.get("version") == version), None)

    title = f"## {version}"
    if entry and entry.get("date"):
        title += f" ({entry['date']})"

    lines = [title, ""]
    if entry:
        for item in entry.get("items", []):
            lines.append(f"- **{item.get('type', '更新')}** {item.get('text', '')}")
    lines += ["", "下载 `tgmedia.fpk`，在飞牛应用中心手动安装。"]
    print("\n".join(lines))


if __name__ == "__main__":
    main()
