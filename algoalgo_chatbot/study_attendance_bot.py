import discord
from discord.ext import commands
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

DATA_FILE = "study_data.json"
STUDY_HOURS = 2  # 기본 출석 시간

# ==================== 데이터 관리 ====================

def load_data():
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_user_data(user_id):
    data = load_data()
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            'name': '',
            'records': {}
        }
        save_data(data)

    return user_id, data

# ==================== 봇 시작 ====================

@bot.event
async def on_ready():
    print(f'{bot.user} 로그인 성공!')

# ==================== 출석 ====================

@bot.command(name='출석')
async def study_attendance(ctx, *, content: str = None):
    user_id, data = get_user_data(ctx.author.id)

    # 파싱
    parts = content.split() if content else []

    hours = STUDY_HOURS
    content_text = "기록 없음"

    if parts:
        try:
            hours = float(parts[0])
            content_text = " ".join(parts[1:]) if len(parts) > 1 else "기록 없음"
        except ValueError:
            content_text = " ".join(parts)

    today = datetime.now().strftime('%Y-%m-%d')

    data[user_id]['name'] = ctx.author.name

    if today in data[user_id]['records']:
        await ctx.send(f"{ctx.author.mention} 이미 출석함")
        return

    data[user_id]['records'][today] = {
        'hours': hours,
        'content': content_text,
        'timestamp': datetime.now().isoformat()
    }
    save_data(data)

    await ctx.send(f"출석 완료: {hours}시간 / {content_text}")

# ==================== 출석 수정 ====================

@bot.command(name='출석수정')
async def edit_attendance(ctx, *, args: str = None):
    user_id, data = get_user_data(ctx.author.id)

    parts = args.split() if args else []

    date = None
    hours = None

    # 날짜 판별
    if parts and '-' in parts[0]:
        date = parts.pop(0)

    # 시간 판별
    if parts:
        try:
            hours = float(parts[0])
            parts.pop(0)
        except ValueError:
            pass

    content = " ".join(parts) if parts else None

    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    if date not in data[user_id]['records']:
        await ctx.send("기록 없음")
        return

    record = data[user_id]['records'][date]

    if hours is not None:
        record['hours'] = hours
    if content is not None:
        record['content'] = content

    save_data(data)

    await ctx.send(f"수정 완료: {date} / {record['hours']}시간 / {record['content']}")

# ==================== 오늘 기록 ====================

@bot.command(name='오늘기록')
async def today_record(ctx):
    user_id, data = get_user_data(ctx.author.id)
    today = datetime.now().strftime('%Y-%m-%d')

    records = data[user_id]['records']

    if today not in records:
        await ctx.send("오늘 기록 없음")
        return

    r = records[today]
    await ctx.send(f"{today} / {r['hours']}시간 / {r['content']}")

# ==================== 개인 통계 ====================

@bot.command(name='개인통계')
async def personal_stats(ctx):
    user_id, data = get_user_data(ctx.author.id)
    records = data[user_id]['records']

    if not records:
        await ctx.send("기록 없음")
        return

    total_hours = sum(r['hours'] for r in records.values())
    total_days = len(records)

    await ctx.send(f"총 {total_days}일 / {total_hours}시간")
    # ==================== 도움말 ===================

@bot.command(name='도움말')
async def help_command(ctx):
    embed = discord.Embed(
    title="📚 스터디 출석 봇 도움말",
    description="핵심 명령어만 빠르게 확인하세요!",
    color=discord.Color.teal()
)

    # 기본 개념
    embed.add_field(
        name="📌 기본",
        value="• 하루 1회 출석\n"
              "• 기본 2시간 (변경 가능)\n"
              "• 공부 내용 기록 가능",
        inline=False
    )

    # 출석
    embed.add_field(
        name="🎯 출석",
        value="`!출석`\n"
              "`!출석 알고리즘`\n"
              "`!출석 3 알고리즘`\n\n"
              "👉 시간 생략 시 2시간",
        inline=False
    )

    # 출석 수정
    embed.add_field(
        name="🔄 출석 수정",
        value="`!출석수정 3 공부`\n"
              "`!출석수정 공부`\n"
              "`!출석수정 2024-01-01 3 수정`\n\n"
              "👉 날짜 생략 시 오늘",
        inline=False
    )

    # 조회
    embed.add_field(
        name="📊 조회",
        value="`!오늘기록`\n"
              "`!개인통계`\n"
              "`!주간통계`\n"
              "`!월간통계 2024-01`",
        inline=False
    )

    # 기록
    embed.add_field(
        name="📚 학습 기록",
        value="`!학습기록`\n"
              "`!학습기록 30`\n"
              "`!학습기록 14 @유저`",
        inline=False
    )

    # 관리자
    embed.add_field(
        name="👨‍💼 관리자",
        value="`!전체주간통계`\n"
              "`!전체월간통계`\n"
              "`!출석현황`",
        inline=False
    )

    embed.set_footer(text="💡 !출석 2 공부내용 ← 이게 가장 많이 쓰는 형태")

    await ctx.send(embed=embed)

# ==================== 실행 ====================

if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")
    bot.run(TOKEN)

