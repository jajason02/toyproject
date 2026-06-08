"""
toyproject README 자동 생성 스크립트

각 프로젝트 폴더의 README.md 에서 메타 정보를 읽어
루트 README.md 를 자동으로 갱신합니다.

프로젝트 README.md 양식:
    > 한 줄 설명 (blockquote 첫 번째 줄)

    | 항목 | 내용 |
    |:---|:---|
    | 기술 스택 | Spring Boot · JPA |
    | 주요 기능 | Todo CRUD |
    | 기간 | 2026-06 |

실행: python .github/scripts/generate_readme.py
      (또는 pre-commit hook 으로 자동 실행)
"""

import re
from pathlib import Path
from datetime import date

ROOT = Path(__file__).parent.parent.parent

EXCLUDE = {".git", ".github", "__pycache__", "node_modules", ".venv", "venv"}


# ── 수집 ────────────────────────────────────────────────

def get_project_dirs() -> list[Path]:
    """루트 하위에서 README.md 가 있는 폴더만 알파벳 순으로 반환."""
    return sorted(
        p for p in ROOT.iterdir()
        if p.is_dir()
        and p.name not in EXCLUDE
        and not p.name.startswith(".")
        and (p / "README.md").exists()
    )


def parse_project(project_dir: Path) -> dict:
    """프로젝트 폴더의 README.md 에서 메타 정보 추출."""
    text = (project_dir / "README.md").read_text(encoding="utf-8")
    name = project_dir.name

    # blockquote 첫 줄을 한 줄 설명으로 사용
    desc = ""
    bq = re.search(r"^>\s+(.+)", text, re.MULTILINE)
    if bq:
        desc = bq.group(1).strip()
    else:
        # fallback: h1/h2 중 폴더명과 다른 첫 제목
        for line in text.splitlines():
            line = line.strip()
            if line.startswith(("# ", "## ")):
                candidate = re.sub(r"^#{1,2}\s+", "", line).strip()
                if candidate.lower() != name.lower():
                    desc = candidate
                    break

    # 테이블 파싱
    stack = features = period = ""
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        key, val = cells[0], cells[1]
        if "기술" in key or "stack" in key.lower():
            stack = val
        elif "기능" in key or "feature" in key.lower():
            features = val
        elif "기간" in key or "period" in key.lower():
            period = val

    return {"name": name, "desc": desc, "stack": stack,
            "features": features, "period": period}


# ── 렌더 ────────────────────────────────────────────────

def render(projects: list[dict]) -> str:
    today = date.today().strftime("%Y-%m-%d")
    total = len(projects)

    toc = " &nbsp;·&nbsp; ".join(
        f"[{p['name']}](#{p['name']})" for p in projects
    )

    lines = [
        "# 🧸 toyproject\n",
        "학습 목적의 토이 프로젝트 모음입니다.  ",
        "각 폴더는 독립된 프로젝트로, 스택 학습 및 포트폴리오 목적으로 제작했습니다.\n",
        "---\n",
        f"Total **{total}** &nbsp;·&nbsp; Last updated **{today}**\n",
        "---\n",
        toc + "\n",
        "---\n",
    ]

    for p in projects:
        lines.append(f"## {p['name']}\n")
        if p["desc"]:
            lines.append(f"> {p['desc']}\n")
        lines.append("| 항목 | 내용 |")
        lines.append("|:---|:---|")
        if p["stack"]:
            lines.append(f"| 기술 스택 | {p['stack']} |")
        if p["features"]:
            lines.append(f"| 주요 기능 | {p['features']} |")
        if p["period"]:
            lines.append(f"| 기간 | {p['period']} |")
        lines.append("")

    lines += [
        "---\n",
        '<p align="right"><em>"만들면서 배운다"</em></p>\n',
    ]

    return "\n".join(lines) + "\n"


# ── 메인 ────────────────────────────────────────────────

if __name__ == "__main__":
    projects = [parse_project(d) for d in get_project_dirs()]

    if not projects:
        print("⚠️  README.md 가 있는 프로젝트 폴더를 찾지 못했습니다.")
    else:
        readme = render(projects)
        (ROOT / "README.md").write_text(readme, encoding="utf-8")
        print(f"Done — {len(projects)} projects")
