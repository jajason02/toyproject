"""
toyproject README 자동 갱신 스크립트 (append 방식)

동작:
  - 루트 README.md 에 이미 섹션이 있는 프로젝트는 건드리지 않음
  - 새 폴더가 생긴 경우에만 섹션을 맨 아래에 추가
  - 헤더(Total / TOC / 날짜)만 항상 갱신

실행: python .github/scripts/generate_readme.py
"""

import re
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent.parent.parent
README = ROOT / "README.md"

EXCLUDE = {".git", ".github", "__pycache__", "node_modules", ".venv", "venv"}

HEADER = """\
# toyproject

학습 목적의 토이 프로젝트 모음입니다.

---

Total **{total}** &nbsp;·&nbsp; Last updated **{today}**

---

{toc}

---
"""

NEW_SECTION = """\
## [{name}](./{name})
추가: {today}

**개요**
(작성)

**기술 스택**
(작성)"""


def get_project_dirs() -> list[Path]:
    return sorted(
        p for p in ROOT.iterdir()
        if p.is_dir()
        and p.name not in EXCLUDE
        and not p.name.startswith(".")
    )


def extract_section_name(header_line: str) -> str:
    """## [name](link) 또는 ## name 에서 name 추출."""
    m = re.match(r"^## \[([^\]]+)\]", header_line)
    if m:
        return m.group(1).strip()
    m = re.match(r"^## (.+)", header_line)
    if m:
        return m.group(1).strip()
    return ""


def parse_sections(text: str) -> list[str]:
    """## 기준으로 섹션 분리, 각 섹션 앞뒤 --- 제거."""
    first_h2 = re.search(r"^## ", text, re.MULTILINE)
    if not first_h2:
        return []

    body = text[first_h2.start():]
    sections = []
    for chunk in re.split(r"(?=^## )", body, flags=re.MULTILINE):
        # 앞뒤 공백 및 --- 제거
        chunk = chunk.strip().strip("---").strip()
        if chunk.startswith("## "):
            sections.append(chunk)
    return sections


def get_existing_names(sections: list[str]) -> set[str]:
    names = set()
    for s in sections:
        name = extract_section_name(s.splitlines()[0])
        if name:
            names.add(name)
    return names


def main():
    today = date.today().strftime("%Y-%m-%d")
    projects = get_project_dirs()

    if not projects:
        print("⚠️  프로젝트 폴더를 찾지 못했습니다.")
        return

    sections = parse_sections(README.read_text(encoding="utf-8")) if README.exists() else []
    existing_names = get_existing_names(sections)
    project_names = {p.name for p in projects}

    removed = existing_names - project_names
    if removed:
        print(f"  ℹ️  폴더 없음 (섹션 유지): {', '.join(sorted(removed))}")

    added = []
    for p in projects:
        if p.name not in existing_names:
            sections.append(NEW_SECTION.format(name=p.name, today=today))
            added.append(p.name)

    if added:
        print(f"  ✅ 새 프로젝트 추가: {', '.join(added)}")
    else:
        print("  ✅ 새 프로젝트 없음 (헤더/TOC만 갱신)")

    all_names = [extract_section_name(s.splitlines()[0]) for s in sections]
    all_names = [n for n in all_names if n]

    toc = " &nbsp;·&nbsp; ".join(f"[{n}](#{n})" for n in all_names)
    header = HEADER.format(total=len(all_names), today=today, toc=toc)
    body = "\n\n---\n\n".join(sections)
    README.write_text(header + "\n" + body + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()