"""
update_readme.py
----------------
toyproject/ 루트에서 실행하면 각 프로젝트 폴더의 README.md를 읽어
루트 README.md를 자동으로 갱신합니다.

사용법:
    python update_readme.py          # 수동 실행
    python update_readme.py --check  # 변경사항만 확인 (실제 수정 X)
"""

import os
import re
import argparse
from datetime import date
from pathlib import Path

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────

# README로 인식하지 않을 폴더 (루트 레벨에서 제외)
EXCLUDE_DIRS = {".git", ".github", "__pycache__", "node_modules", ".venv", "venv"}

ROOT_README = Path("README.md")

TEMPLATE_HEADER = """\
# 🧸 toyproject

학습 목적의 토이 프로젝트 모음입니다.  
각 폴더는 독립된 프로젝트로, 스택 학습 및 포트폴리오 목적으로 제작했습니다.

---

Total **{total}** &nbsp;·&nbsp; Last updated **{today}**

---

{toc}

---
"""

TEMPLATE_FOOTER = """
---

<p align="right"><em>"만들면서 배운다"</em></p>
"""


# ──────────────────────────────────────────────
# 프로젝트 폴더 수집
# ──────────────────────────────────────────────

def get_project_dirs() -> list[Path]:
    """루트의 하위 폴더 중 README.md가 있는 것만 반환 (알파벳 순)."""
    projects = []
    for p in sorted(Path(".").iterdir()):
        if p.is_dir() and p.name not in EXCLUDE_DIRS and not p.name.startswith("."):
            if (p / "README.md").exists():
                projects.append(p)
    return projects


# ──────────────────────────────────────────────
# 프로젝트 README 파싱
# ──────────────────────────────────────────────

def parse_project_readme(project_dir: Path) -> dict:
    """
    프로젝트 폴더의 README.md에서 메타정보를 추출합니다.

    README.md 상단에 아래 형식의 테이블이 있으면 자동 파싱:

        | 항목 | 내용 |
        |:---|:---|
        | 기술 스택 | FastAPI · Vue.js · Gemini AI |
        | 주요 기능 | 금융상품 비교 / AI 추천 |
        | 기간 | 2026-05 |

    없으면 폴더명만 사용하고 나머지는 빈값으로 처리합니다.
    """
    readme_path = project_dir / "README.md"
    text = readme_path.read_text(encoding="utf-8")

    name = project_dir.name

    # 첫 번째 h1/h2 제목을 설명으로 사용
    desc = ""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("# ") or line.startswith("## "):
            candidate = re.sub(r"^#{1,2}\s+", "", line).strip()
            # 폴더명과 동일한 제목은 skip
            if candidate.lower() != name.lower():
                desc = candidate
                break

    # blockquote > 로 시작하는 한 줄 설명 우선 적용
    bq_match = re.search(r"^>\s+(.+)", text, re.MULTILINE)
    if bq_match:
        desc = bq_match.group(1).strip()

    # 테이블 파싱
    stack = ""
    features = ""
    period = ""

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        key, val = cells[0], cells[1]
        if "기술" in key or "stack" in key.lower():
            stack = val
        elif "기능" in key or "feature" in key.lower():
            features = val
        elif "기간" in key or "period" in key.lower() or "date" in key.lower():
            period = val

    return {
        "name": name,
        "desc": desc,
        "stack": stack,
        "features": features,
        "period": period,
    }


# ──────────────────────────────────────────────
# README 섹션 생성
# ──────────────────────────────────────────────

def build_project_section(info: dict) -> str:
    lines = [f"## {info['name']}"]

    if info["desc"]:
        lines.append(f"\n> {info['desc']}")

    lines.append("\n| 항목 | 내용 |")
    lines.append("|:---|:---|")

    if info["stack"]:
        lines.append(f"| 기술 스택 | {info['stack']} |")
    if info["features"]:
        lines.append(f"| 주요 기능 | {info['features']} |")
    if info["period"]:
        lines.append(f"| 기간 | {info['period']} |")

    return "\n".join(lines)


def build_readme(projects: list[dict]) -> str:
    today = date.today().strftime("%Y-%m-%d")
    total = len(projects)

    toc = " &nbsp;·&nbsp; ".join(
        f"[{p['name']}](#{p['name']})" for p in projects
    )

    header = TEMPLATE_HEADER.format(total=total, today=today, toc=toc)

    sections = "\n\n".join(build_project_section(p) for p in projects)

    return header + sections + TEMPLATE_FOOTER


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="toyproject README 자동 갱신")
    parser.add_argument(
        "--check",
        action="store_true",
        help="변경 여부만 확인하고 파일은 수정하지 않음",
    )
    args = parser.parse_args()

    project_dirs = get_project_dirs()

    if not project_dirs:
        print("⚠️  README.md가 있는 프로젝트 폴더를 찾지 못했습니다.")
        print("   각 프로젝트 폴더 안에 README.md가 있는지 확인해 주세요.")
        return

    print(f"📂 프로젝트 {len(project_dirs)}개 발견:")
    projects = []
    for d in project_dirs:
        info = parse_project_readme(d)
        projects.append(info)
        print(f"   - {info['name']}")

    new_content = build_readme(projects)

    if args.check:
        current = ROOT_README.read_text(encoding="utf-8") if ROOT_README.exists() else ""
        if current == new_content:
            print("\n✅ README.md 변경사항 없음")
        else:
            print("\n🔄 README.md 변경사항 있음 (--check 모드이므로 수정하지 않음)")
        return

    ROOT_README.write_text(new_content, encoding="utf-8")
    print(f"\n✅ README.md 갱신 완료 ({date.today().strftime('%Y-%m-%d')})")


if __name__ == "__main__":
    main()
