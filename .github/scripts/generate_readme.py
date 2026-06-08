"""
toyproject README 자동 갱신 스크립트 (append 방식)

동작:
  - 루트 README.md 에 이미 ## 프로젝트명 섹션이 있으면 건드리지 않음
  - 새 폴더가 생긴 경우에만 섹션을 맨 아래에 추가
  - 헤더(Total / TOC)의 숫자와 날짜만 항상 갱신

새 프로젝트 추가 시 생성되는 골격:
  ## 프로젝트명
  [→ 폴더 바로가기](./프로젝트명)
  추가: YYYY-MM-DD

  **개요**
  (작성)

  **기술 스택**
  (작성)

실행: python .github/scripts/generate_readme.py
"""

import re
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent.parent.parent
README = ROOT / "README.md"

EXCLUDE = {".git", ".github", "__pycache__", "node_modules", ".venv", "venv"}

HEADER = """\
# 🧸 toyproject

학습 목적의 토이 프로젝트 모음입니다.

---

Total **{total}** &nbsp;·&nbsp; Last updated **{today}**

---

{toc}

---
"""

FOOTER = """\

---

<p align="right"><em>"만들면서 배운다"</em></p>
"""

NEW_SECTION = """\
## {name}
[→ 폴더 바로가기](./{name}) &nbsp; | &nbsp; 추가: {today}

**개요**
(작성)

**기술 스택**
(작성)
"""


# ── 폴더 수집 ────────────────────────────────────────────

def get_project_dirs() -> list[Path]:
    return sorted(
        p for p in ROOT.iterdir()
        if p.is_dir()
        and p.name not in EXCLUDE
        and not p.name.startswith(".")
    )


# ── README 파싱 ──────────────────────────────────────────

def parse_existing(text: str) -> tuple[str, str, list[str]]:
    """
    기존 README 에서 헤더 / 바디(섹션들) / 푸터 분리.
    반환: (header_raw, footer_raw, sections)
      sections: ['## proj1\n...', '## proj2\n...', ...]
    """
    # 헤더: 첫 번째 ## 이전까지
    first_h2 = re.search(r"^## ", text, re.MULTILINE)
    if first_h2:
        header = text[:first_h2.start()]
        rest = text[first_h2.start():]
    else:
        header = text
        rest = ""

    # 푸터: 마지막 --- 이후 (footer 마커)
    footer_match = re.search(r"\n---\n\n<p align", rest)
    if footer_match:
        footer = rest[footer_match.start():]
        body = rest[:footer_match.start()]
    else:
        footer = FOOTER
        body = rest

    # 섹션 분리: ## 기준으로 split
    sections = []
    for chunk in re.split(r"(?=^## )", body, flags=re.MULTILINE):
        chunk = chunk.strip()
        if chunk:
            sections.append(chunk)

    return header, footer, sections


def get_existing_names(sections: list[str]) -> set[str]:
    names = set()
    for s in sections:
        m = re.match(r"^## (.+)", s)
        if m:
            names.add(m.group(1).strip())
    return names


# ── 헤더 재생성 ──────────────────────────────────────────

def build_header(projects: list[Path]) -> str:
    today = date.today().strftime("%Y-%m-%d")
    total = len(projects)
    toc = " &nbsp;·&nbsp; ".join(
        f"[{p.name}](#{p.name})" for p in projects
    )
    return HEADER.format(total=total, today=today, toc=toc)


# ── 메인 ────────────────────────────────────────────────

def main():
    today = date.today().strftime("%Y-%m-%d")
    projects = get_project_dirs()

    if not projects:
        print("⚠️  프로젝트 폴더를 찾지 못했습니다.")
        return

    # 기존 README 읽기
    if README.exists():
        text = README.read_text(encoding="utf-8")
        _, footer, sections = parse_existing(text)
    else:
        footer = FOOTER
        sections = []

    existing_names = get_existing_names(sections)
    project_names = {p.name for p in projects}

    # 삭제된 프로젝트 폴더 감지 (섹션은 남겨두되 로그만)
    removed = existing_names - project_names
    if removed:
        print(f"  ℹ️  폴더 없음 (섹션 유지): {', '.join(sorted(removed))}")

    # 새 프로젝트 섹션 append
    added = []
    for p in projects:
        if p.name not in existing_names:
            sections.append(
                NEW_SECTION.format(name=p.name, today=today).strip()
            )
            added.append(p.name)

    if added:
        print(f"  ✅ 새 프로젝트 추가: {', '.join(added)}")
    else:
        print("  ✅ 새 프로젝트 없음 (헤더/TOC만 갱신)")

    # 최종 README 조합
    # TOC는 섹션에 실제로 있는 이름 기준으로 (삭제된 폴더 포함)
    all_names = []
    for s in sections:
        m = re.match(r"^## (.+)", s)
        if m:
            all_names.append(m.group(1).strip())

    today_str = date.today().strftime("%Y-%m-%d")
    toc = " &nbsp;·&nbsp; ".join(f"[{n}](#{n})" for n in all_names)
    header = HEADER.format(total=len(all_names), today=today_str, toc=toc)

    body = "\n\n".join(sections)
    output = header + body + footer

    README.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    main()