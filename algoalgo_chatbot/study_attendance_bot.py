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
STUDY_HOURS = 2  # 필수 출석 시간 (2시간)

# ==================== 데이터 관리 함수 ====================

def load_data():
    if Path(DATA_FILE).exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_user_data(user_id):
    """사용자 데이터 가져오기 (없으면 생성)"""
    data = load_data()
    user_id = str(user_id)

    if user_id not in data:
        data[user_id] = {
            'name': '',
            'records': {}  # {'2024-01-15': {'hours': 2, 'content': '...'}}
        }
        save_data(data)

    return user_id, data

# ==================== 봇 시작 ====================

@bot.event
async def on_ready():
    print(f'{bot.user} 로그인 성공!')
    print(f'봇이 준비되었습니다.')
    print(f'출석 채널 ID: {STUDY_CHANNEL_ID}')

@bot.event
async def on_command_error(ctx, error):
    """명령어 에러 처리"""
    if isinstance(error, commands.CheckFailure):
        # 채널 제한 에러
        embed = discord.Embed(
            title="❌ 사용 불가능",
            description=f"이 명령어는 <#{STUDY_CHANNEL_ID}> 채널에서만 사용할 수 있습니다!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=5)
    elif isinstance(error, commands.MissingPermissions):
        # 관리자 권한 에러
        embed = discord.Embed(
            title="⚠️ 권한 없음",
            description="이 명령어는 관리자만 사용할 수 있습니다!",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed, delete_after=5)
    else:
        raise error

# ==================== 채널 확인 함수 ====================

STUDY_CHANNEL_ID = STUDY_CHANNEL_ID = 1501576735467245660  # 👈 여기에 채널 ID 입력
# 👈 여기에 채널 ID 입력

def is_study_channel(ctx):
    """지정된 채널에서만 명령어 사용 가능"""
    return ctx.channel.id == STUDY_CHANNEL_ID

# ==================== 출석 관련 명령어 ====================

@bot.command(name='출석')
@commands.check(is_study_channel)
async def study_attendance(ctx, *, input_text: str = None):
    """
    스터디 출석 기록
    사용법: !출석 2 파이썬 강의 복습, 알고리즘 문제 풀이
    (시간을 생략하고 내용만 적어도 기본 출석 시간으로 자동 기록됩니다)
    """
    user_id, data = get_user_data(ctx.author.id)

    # 기본값 설정
    hours = STUDY_HOURS
    content = None

    if input_text:
        parts = input_text.split(maxsplit=1)
        try:
            # 첫 번째 입력값이 숫자인지 확인
            hours = float(parts[0])
            if len(parts) > 1:
                content = parts[1]
        except ValueError:
            # 숫자가 아니라면 입력값 전체를 내용으로 취급
            content = input_text

    today = datetime.now().strftime('%Y-%m-%d')

    # 이름 업데이트
    data[user_id]['name'] = ctx.author.name

    # 오늘 이미 출석했는지 확인
    if today in data[user_id]['records']:
        embed = discord.Embed(
            title="⚠️ 출석 실패",
            description=f"{ctx.author.mention}님은 이미 오늘 출석하셨습니다!",
            color=discord.Color.orange()
        )
        embed.add_field(name="기존 기록", value=f"{data[user_id]['records'][today]['hours']}시간\n{data[user_id]['records'][today]['content']}", inline=False)
        await ctx.send(embed=embed)
        return

    # 출석 기록 저장
    data[user_id]['records'][today] = {
        'hours': hours,
        'content': content if content else "기록 없음",
        'timestamp': datetime.now().isoformat()
    }
    save_data(data)

    # 성공 메시지
    embed = discord.Embed(
        title="✅ 출석 완료",
        color=discord.Color.green()
    )
    embed.add_field(name="👤 이름", value=ctx.author.name, inline=False)
    embed.add_field(name="📅 날짜", value=today, inline=False)
    embed.add_field(name="⏰ 공부 시간", value=f"{hours}시간", inline=False)
    embed.add_field(name="📝 오늘 할 일", value=content if content else "기록 없음", inline=False)
    embed.set_footer(text=f"시간: {datetime.now().strftime('%H:%M:%S')}")

    await ctx.send(embed=embed)

@bot.command(name='출석수정')
@commands.check(is_study_channel)
async def edit_attendance(ctx, *, input_text: str = None):
    """
    출석 기록 수정
    사용법: !출석수정 2024-01-15 3 새로운 내용
    날짜 생략 시 오늘 기록이 수정되며, 시간도 유연하게 생략할 수 있습니다.
    """
    user_id, data = get_user_data(ctx.author.id)

    date = datetime.now().strftime('%Y-%m-%d')
    hours = None
    content = None

    if input_text:
        parts = input_text.split()
        idx = 0

        # 1. 첫 번째 인자가 날짜 형태(YYYY-MM-DD)인지 확인
        if len(parts) > idx:
            try:
                datetime.strptime(parts[idx], '%Y-%m-%d')
                date = parts[idx]
                idx += 1
            except ValueError:
                pass

        # 2. 다음 인자가 시간(숫자)인지 확인
        if len(parts) > idx:
            try:
                hours = float(parts[idx])
                idx += 1
            except ValueError:
                pass

        # 3. 나머지는 내용으로 합침
        if len(parts) > idx:
            content = " ".join(parts[idx:])

    # 해당 날짜 확인
    if date not in data[user_id]['records']:
        embed = discord.Embed(
            title="❌ 기록 없음",
            description=f"{date}에 출석 기록이 없습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # 수정
    record = data[user_id]['records'][date]
    if hours is not None:
        record['hours'] = hours
    if content is not None:
        record['content'] = content

    save_data(data)

    embed = discord.Embed(
        title="🔄 출석 기록 수정 완료",
        color=discord.Color.blue()
    )
    embed.add_field(name="📅 날짜", value=date, inline=False)
    embed.add_field(name="⏰ 공부 시간", value=f"{record['hours']}시간", inline=False)
    embed.add_field(name="📝 내용", value=record['content'], inline=False)

    await ctx.send(embed=embed)

# ==================== 조회 명령어 ====================

@bot.command(name='개인통계')
@commands.check(is_study_channel)
async def personal_stats(ctx, member: discord.Member = None):
    """개인 전체 출석 통계"""
    if member is None:
        member = ctx.author

    user_id, data = get_user_data(member.id)
    records = data[user_id]['records']

    if not records:
        embed = discord.Embed(
            title="📊 출석 기록 없음",
            description=f"{member.mention}님의 출석 기록이 없습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    total_hours = sum(r['hours'] for r in records.values())
    total_days = len(records)
    avg_hours = total_hours / total_days if total_days > 0 else 0

    embed = discord.Embed(
        title=f"📊 {member.name}님의 전체 통계",
        color=discord.Color.blue()
    )
    embed.add_field(name="📅 총 출석일", value=f"{total_days}일", inline=True)
    embed.add_field(name="⏰ 총 공부시간", value=f"{total_hours}시간", inline=True)
    embed.add_field(name="📈 평균 시간/일", value=f"{avg_hours:.1f}시간", inline=True)

    await ctx.send(embed=embed)

@bot.command(name='주간통계')
@commands.check(is_study_channel)
async def weekly_stats(ctx, member: discord.Member = None):
    """이번주 출석 통계"""
    if member is None:
        member = ctx.author

    user_id, data = get_user_data(member.id)
    records = data[user_id]['records']

    # 이번주 월요일 계산
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    weekly_records = {}
    for date_str, record in records.items():
        date = datetime.strptime(date_str, '%Y-%m-%d')
        if monday <= date <= today:
            weekly_records[date_str] = record

    if not weekly_records:
        embed = discord.Embed(
            title="📅 이번주 출석 없음",
            description=f"{member.mention}님이 이번주에 출석하지 않았습니다.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    total_hours = sum(r['hours'] for r in weekly_records.values())
    total_days = len(weekly_records)

    # 요일별 상세 정보
    details = ""
    for date_str in sorted(weekly_records.keys()):
        record = weekly_records[date_str]
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        day_name = ['월', '화', '수', '목', '금', '토', '일'][date_obj.weekday()]
        details += f"**{date_str} ({day_name})**: {record['hours']}시간 - {record['content'][:30]}\n"

    embed = discord.Embed(
        title=f"📅 {member.name}님의 이번주 통계",
        description=f"{monday.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')}",
        color=discord.Color.purple()
    )
    embed.add_field(name="📊 출석일", value=f"{total_days}일", inline=True)
    embed.add_field(name="⏰ 총 시간", value=f"{total_hours}시간", inline=True)
    embed.add_field(name="📝 상세 기록", value=details if details else "없음", inline=False)

    await ctx.send(embed=embed)

@bot.command(name='월간통계')
@commands.check(is_study_channel)
async def monthly_stats(ctx, year_month: str = None, member: discord.Member = None):
    """월간 출석 통계
    사용법: !월간통계 또는 !월간통계 2024-01 또는 !월간통계 2024-01 @사용자
    """
    if member is None:
        member = ctx.author

    user_id, data = get_user_data(member.id)
    records = data[user_id]['records']

    # 년도-월 결정
    if year_month is None:
        year_month = datetime.now().strftime('%Y-%m')

    # 해당 월의 기록 필터링
    monthly_records = {}
    for date_str, record in records.items():
        if date_str.startswith(year_month):
            monthly_records[date_str] = record

    if not monthly_records:
        embed = discord.Embed(
            title="❌ 기록 없음",
            description=f"{year_month}에 출석 기록이 없습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    total_hours = sum(r['hours'] for r in monthly_records.values())
    total_days = len(monthly_records)

    # 상세 기록
    details = ""
    for date_str in sorted(monthly_records.keys()):
        record = monthly_records[date_str]
        details += f"**{date_str}**: {record['hours']}시간 - {record['content'][:40]}\n"

    embed = discord.Embed(
        title=f"📊 {member.name}님의 {year_month} 통계",
        color=discord.Color.gold()
    )
    embed.add_field(name="📅 출석일", value=f"{total_days}일", inline=True)
    embed.add_field(name="⏰ 총 시간", value=f"{total_hours}시간", inline=True)
    embed.add_field(name="📈 평균 시간/일", value=f"{total_hours/total_days:.1f}시간", inline=True)

    # 너무 길면 자르기
    if len(details) > 1024:
        details = details[:1000] + "..."

    embed.add_field(name="📝 상세 기록", value=details, inline=False)

    await ctx.send(embed=embed)

@bot.command(name='오늘기록')
@commands.check(is_study_channel)
async def today_record(ctx, member: discord.Member = None):
    """오늘의 기록 조회"""
    if member is None:
        member = ctx.author

    user_id, data = get_user_data(member.id)
    today = datetime.now().strftime('%Y-%m-%d')
    records = data[user_id]['records']

    if today not in records:
        embed = discord.Embed(
            title="❌ 오늘 출석 없음",
            description=f"{member.mention}님이 오늘 출석하지 않았습니다.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    record = records[today]
    embed = discord.Embed(
        title=f"📋 {member.name}님의 오늘 기록",
        color=discord.Color.green()
    )
    embed.add_field(name="📅 날짜", value=today, inline=False)
    embed.add_field(name="⏰ 공부 시간", value=f"{record['hours']}시간", inline=False)
    embed.add_field(name="📝 오늘 할 일", value=record['content'], inline=False)

    await ctx.send(embed=embed)

# ==================== 관리자 명령어 ====================

@bot.command(name='전체주간통계')
@commands.has_permissions(administrator=True)
@commands.check(is_study_channel)
async def all_weekly_stats(ctx):
    """전체 사용자의 이번주 통계"""
    data = load_data()

    if not data:
        await ctx.send("출석 기록이 없습니다.")
        return

    # 이번주 계산
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())

    # 사용자별 이번주 통계 계산
    weekly_stats_dict = {}
    for user_id, user_data in data.items():
        weekly_total = 0
        weekly_days = 0
        for date_str, record in user_data['records'].items():
            date = datetime.strptime(date_str, '%Y-%m-%d')
            if monday <= date <= today:
                weekly_total += record['hours']
                weekly_days += 1

        if weekly_days > 0:  # 이번주에 출석한 사람만
            weekly_stats_dict[user_data['name']] = {
                'days': weekly_days,
                'hours': weekly_total,
                'avg': weekly_total / weekly_days
            }

    if not weekly_stats_dict:
        await ctx.send("이번주 출석 기록이 없습니다.")
        return

    # 출석일 순으로 정렬
    sorted_stats = sorted(weekly_stats_dict.items(), key=lambda x: x[1]['hours'], reverse=True)

    leaderboard = ""
    for i, (name, stats) in enumerate(sorted_stats, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}️⃣"
        leaderboard += f"{medal} **{name}**: {stats['hours']}시간 ({stats['days']}일, 평균 {stats['avg']:.1f}h)\n"

    embed = discord.Embed(
        title=f"📅 이번주 전체 통계 ({monday.strftime('%m-%d')} ~ {today.strftime('%m-%d')})",
        description=leaderboard,
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"총 참여자: {len(sorted_stats)}")

    await ctx.send(embed=embed)

@bot.command(name='전체월간통계')
@commands.has_permissions(administrator=True)
@commands.check(is_study_channel)
async def all_monthly_stats(ctx, year_month: str = None):
    """전체 사용자의 월간 통계"""
    if year_month is None:
        year_month = datetime.now().strftime('%Y-%m')

    data = load_data()

    if not data:
        await ctx.send("출석 기록이 없습니다.")
        return

    # 사용자별 월간 통계 계산
    monthly_stats_dict = {}
    for user_id, user_data in data.items():
        monthly_total = 0
        monthly_days = 0
        for date_str, record in user_data['records'].items():
            if date_str.startswith(year_month):
                monthly_total += record['hours']
                monthly_days += 1

        if monthly_days > 0:
            monthly_stats_dict[user_data['name']] = {
                'days': monthly_days,
                'hours': monthly_total,
                'avg': monthly_total / monthly_days
            }

    if not monthly_stats_dict:
        await ctx.send(f"{year_month}에 출석 기록이 없습니다.")
        return

    # 시간 순으로 정렬
    sorted_stats = sorted(monthly_stats_dict.items(), key=lambda x: x[1]['hours'], reverse=True)

    leaderboard = ""
    for i, (name, stats) in enumerate(sorted_stats, 1):
        medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}️⃣"
        leaderboard += f"{medal} **{name}**: {stats['hours']}시간 ({stats['days']}일, 평균 {stats['avg']:.1f}h)\n"

    embed = discord.Embed(
        title=f"📊 {year_month} 전체 통계",
        description=leaderboard,
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"총 참여자: {len(sorted_stats)}")

    await ctx.send(embed=embed)

@bot.command(name='출석현황')
@commands.has_permissions(administrator=True)
@commands.check(is_study_channel)
async def attendance_status(ctx, date: str = None):
    """특정 날짜의 출석 현황
    사용법: !출석현황 또는 !출석현황 2024-01-15
    """
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    data = load_data()
    attendees = []

    for user_id, user_data in data.items():
        if date in user_data['records']:
            record = user_data['records'][date]
            attendees.append({
                'name': user_data['name'],
                'hours': record['hours'],
                'content': record['content']
            })

    if not attendees:
        embed = discord.Embed(
            title=f"❌ {date} 출석 기록 없음",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # 시간 순으로 정렬
    attendees.sort(key=lambda x: x['hours'], reverse=True)

    attendance_str = ""
    for person in attendees:
        attendance_str += f"**{person['name']}**: {person['hours']}시간 - {person['content'][:40]}\n"

    embed = discord.Embed(
        title=f"📋 {date} 출석 현황",
        description=attendance_str,
        color=discord.Color.blue()
    )
    embed.set_footer(text=f"총 {len(attendees)}명 출석")

    await ctx.send(embed=embed)

# ==================== 학습 기록 조회 ====================

@bot.command(name='학습기록')
@commands.check(is_study_channel)
async def learning_history(ctx, days: int = 7, member: discord.Member = None):
    """최근 N일간의 학습 기록 조회
    사용법: !학습기록 7 또는 !학습기록 30 @사용자
    """
    if member is None:
        member = ctx.author

    user_id, data = get_user_data(member.id)
    records = data[user_id]['records']

    # 최근 N일 필터링
    cutoff_date = (datetime.now() - timedelta(days=days)).date()
    recent_records = {}

    for date_str, record in records.items():
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        if date >= cutoff_date:
            recent_records[date_str] = record

    if not recent_records:
        embed = discord.Embed(
            title=f"❌ 최근 {days}일 기록 없음",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # 상세 기록
    history_text = ""
    for date_str in sorted(recent_records.keys(), reverse=True):
        record = recent_records[date_str]
        history_text += f"**{date_str}** ⏰{record['hours']}h\n📝 {record['content']}\n\n"

    # 너무 길면 분할
    if len(history_text) > 4096:
        history_text = history_text[:4000] + "\n... (더 많은 기록)"

    embed = discord.Embed(
        title=f"📚 {member.name}님의 최근 {days}일 학습 기록",
        description=history_text,
        color=discord.Color.blue()
    )

    await ctx.send(embed=embed)

# ==================== 도움말 ====================

@bot.command(name='도움말')
@commands.check(is_study_channel)
async def help_command(ctx):
    """모든 명령어 도움말"""
    embed = discord.Embed(
        title="📚 스터디 출석 봇 명령어",
        color=discord.Color.teal()
    )

    # 출석 관련
    embed.add_field(
        name="🎯 출석 관련",
        value="**!출석** [시간] [내용]\n예: `!출석 2 파이썬 강의 복습, 알고리즘`\n\n"
              "**!출석수정** [날짜] [시간] [내용]\n예: `!출석수정 2024-01-15 3 새로운 내용`\n\n"
              "**!오늘기록** [@사용자] - 오늘의 기록 조회",
        inline=False
    )

    # 개인 통계
    embed.add_field(
        name="📊 개인 통계",
        value="**!개인통계** [@사용자] - 전체 출석 통계\n\n"
              "**!주간통계** [@사용자] - 이번주 통계\n\n"
              "**!월간통계** [2024-01] [@사용자] - 월간 통계",
        inline=False
    )

    # 학습 기록
    embed.add_field(
        name="📚 학습 기록",
        value="**!학습기록** [일수] [@사용자]\n예: `!학습기록 7` - 최근 7일 기록\n\n"
              "예: `!학습기록 30 @사용자` - 특정 사용자 30일 기록",
        inline=False
    )

    # 관리자 명령어
    embed.add_field(
        name="👨‍💼 관리자 명령어",
        value="**!전체주간통계** - 전체 이번주 순위\n\n"
              "**!전체월간통계** [2024-01] - 전체 월간 순위\n\n"
              "**!출석현황** [2024-01-15] - 특정 날짜 출석 현황",
        inline=False
    )

    await ctx.send(embed=embed)

# ==================== 봇 실행 ====================

if __name__ == "__main__":
    TOKEN = os.environ.get("DISCORD_TOKEN")
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN 환경 변수가 설정되지 않았습니다.")
    bot.run(TOKEN)