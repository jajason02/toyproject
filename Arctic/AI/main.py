import asyncio
import json
import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from pydantic import BaseModel

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

client = AsyncOpenAI(
    api_key=os.getenv("GMS_KEY"),
    base_url="https://gms.ssafy.io/gmsapi/api.openai.com/v1",
)
MODEL = "gpt-5.4-mini"


class Message(BaseModel):
    role: str
    content: str


SYSTEM_PROMPT = (
    "당신은 소설 창작 전문 AI입니다. 반드시 지정된 JSON 형식으로만 답하세요. 설명 없이 JSON만 반환하세요. "
    "소설 창작(아이디어 발상, 플롯 구성, 문장 교정, 리뷰 분석, 창작 정보 수집)과 직접 관련 없는 요청 "
    "(폭발물·무기·위험행위, 음식 추천, 일상 상담, 기타 창작 무관 질문)에는 "
    '{"error": "창작 지원 서비스는 소설 창작 관련 요청만 처리합니다."} 형식으로만 답하세요.'
)

GUARDRAIL = (
    "위 입력이 소설 창작과 무관한 일상 대화·질문이거나, 실제 무기·폭발물·위험물 제조 정보 요청이거나, "
    "기타 창작과 직접 관련 없는 내용이라면 "
    '{{"error": "창작 지원 서비스는 소설 창작 관련 요청만 처리합니다."}} 만 반환하세요.\n'
    "칼·폭발·살인 등 단어가 포함되어도 소설 소재나 배경으로 쓰이는 경우라면 정상 처리하세요.\n\n"
)


async def call_openai(prompt: str, history: list[Message] | None = None, temperature: float = 0.7) -> dict:
    messages = [{"role": "developer", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend({"role": m.role, "content": m.content} for m in history)
        messages.append({"role": "user", "content": prompt + "\n반드시 JSON 형식으로만 답하세요."})
    else:
        messages.append({"role": "user", "content": prompt})

    completion = await asyncio.wait_for(
        client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=temperature,
        ),
        timeout=90.0,
    )
    content = completion.choices[0].message.content
    result = json.loads(content)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


# --- 요청/응답 모델 ---

class AnalyzeReviewsRequest(BaseModel):
    reviews: list[str]

class AnalyzeReviewsResponse(BaseModel):
    positive_ratio: float
    negative_ratio: float
    keywords: list[str]
    summary: str


class GenerateIdeasRequest(BaseModel):
    genre: str
    keywords: str
    history: list[Message] = []

class GenerateIdeasResponse(BaseModel):
    ideas: list[str]


class SuggestPlotRequest(BaseModel):
    idea: str
    history: list[Message] = []

class SuggestPlotResponse(BaseModel):
    intro: str
    development: str
    turn: str
    conclusion: str


class CorrectTextRequest(BaseModel):
    text: str
    history: list[Message] = []

class CorrectTextResponse(BaseModel):
    corrected: str
    explanation: str


# --- 엔드포인트 ---

@app.post("/analyze_reviews", response_model=AnalyzeReviewsResponse)
async def analyze_reviews(body: AnalyzeReviewsRequest):
    reviews_text = chr(10).join(f'- {r}' for r in body.reviews)
    prompt = f"""사용자 입력 (도서 리뷰 목록):
{reviews_text}

위 내용이 도서 리뷰가 아니거나 소설 창작과 무관한 일상 대화·질문이라면 {{"error": "창작 지원 서비스는 소설 창작 관련 요청만 처리합니다."}} 만 반환하세요.

도서 리뷰라면 아래 기준으로 직접 분석해서 결과를 JSON 형식으로만 답하세요.

분석 기준:
- positive_ratio: 위 리뷰들을 읽고 긍정적 내용 비율을 0.0~1.0 사이 실수로 계산
- negative_ratio: 부정적 내용 비율을 0.0~1.0 사이 실수로 계산 (positive_ratio + negative_ratio <= 1.0)
- keywords: 리뷰에서 반복 언급된 핵심 단어·표현 5개 (예시 아님, 실제 리뷰 내용 기반)
- summary: 위 리뷰들의 전체적인 독자 반응 한 문장 요약 (예시 아님, 실제 분석 결과)

반드시 위 리뷰를 실제로 분석한 결과만 반환하고, 아래 JSON 형식을 따르세요:
{{
  "positive_ratio": <실제 분석 결과 0.0~1.0>,
  "negative_ratio": <실제 분석 결과 0.0~1.0>,
  "keywords": ["실제키워드1", "실제키워드2", "실제키워드3", "실제키워드4", "실제키워드5"],
  "summary": "실제 분석 요약 문장"
}}"""

    try:
        return await call_openai(prompt, temperature=0.2)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="AI 응답 시간이 초과되었습니다.")
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(status_code=500, detail="AI 응답 파싱에 실패했습니다.")


@app.post("/generate_ideas", response_model=GenerateIdeasResponse)
async def generate_ideas(body: GenerateIdeasRequest):
    prompt = f"""사용자 입력:
- 장르: {body.genre}
- 키워드: {body.keywords}

{GUARDRAIL}창작 관련 요청이라면 장르 '{body.genre}', 키워드 '{body.keywords}'를 바탕으로 단편소설 아이디어 3개를 아래 JSON 형식으로만 답하세요.
각 아이디어는 반드시 아래 요소를 모두 포함해 500자 이상 상세히 작성하세요.
가독성을 위해 각 아이디어 문자열 안에서 아래처럼 큰 항목마다 줄을 나누고, 항목 내용은 탭 문자(\t)로 한 단계 들여쓰기 하세요.
반드시 유효한 JSON으로 반환해야 하므로 문자열 내부 줄바꿈과 탭은 \n, \t escape 문자로 표현하세요:
제목:
\t...
핵심 전제:
\t...
주요 등장인물:
\t- 이름 / 성격 / 역할
시공간 배경:
\t...
핵심 갈등 구조:
\t...
주요 장면:D
\t1. ...
\t2. ...
\t3. ...
{{
  "ideas": [
    "제목:\\n\\t...\\n핵심 전제:\\n\\t...\\n주요 등장인물:\\n\\t...\\n시공간 배경:\\n\\t...\\n핵심 갈등 구조:\\n\\t...\\n주요 장면:\\n\\t1. ...\\n\\t2. ...\\n\\t3. ...",
    "제목:\\n\\t...\\n핵심 전제:\\n\\t...\\n주요 등장인물:\\n\\t...\\n시공간 배경:\\n\\t...\\n핵심 갈등 구조:\\n\\t...\\n주요 장면:\\n\\t1. ...\\n\\t2. ...\\n\\t3. ...",
    "제목:\\n\\t...\\n핵심 전제:\\n\\t...\\n주요 등장인물:\\n\\t...\\n시공간 배경:\\n\\t...\\n핵심 갈등 구조:\\n\\t...\\n주요 장면:\\n\\t1. ...\\n\\t2. ...\\n\\t3. ..."
  ]
}}"""

    try:
        return await call_openai(prompt, body.history or None)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="AI 응답 시간이 초과되었습니다.")
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(status_code=500, detail="AI 응답 파싱에 실패했습니다.")


@app.post("/suggest_plot", response_model=SuggestPlotResponse)
async def suggest_plot(body: SuggestPlotRequest):
    prompt = f"""사용자 입력:
아이디어: {body.idea}

{GUARDRAIL}창작 관련 요청이라면 위 아이디어를 기승전결 구조로 구성해서 아래 JSON 형식으로만 답하세요.
각 단계는 구체적인 장면 묘사, 등장인물의 행동·감정·대화를 포함해 300자 이상 상세히 작성하세요.
입력에 [현재 플롯]과 [이번 수정 요청]이 포함되어 있다면, 초안 아이디어보다 현재 플롯을 우선 기준으로 삼으세요.
사용자가 최근에 바꾼 이름, 사건, 배경, 관계, 결말은 유지하고 예전 설정으로 되돌리지 마세요.
수정 요청이 "줄여줘", "더 길게", "분위기만 바꿔줘"처럼 일부 변경이라면 현재 플롯의 핵심 설정과 직전 수정사항을 보존하세요.
{{
  "intro": "기 — 도입 (300자 이상)",
  "development": "승 — 전개 (300자 이상)",
  "turn": "전 — 전환 (300자 이상)",
  "conclusion": "결 — 결말 (300자 이상)"
}}"""

    try:
        return await call_openai(prompt, body.history or None)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="AI 응답 시간이 초과되었습니다.")
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(status_code=500, detail="AI 응답 파싱에 실패했습니다.")


@app.post("/correct_text", response_model=CorrectTextResponse)
async def correct_text(body: CorrectTextRequest):
    prompt = f"""사용자 입력:
원문: {body.text}

{GUARDRAIL}창작 관련 요청이라면 위 텍스트를 교정하고 아래 JSON 형식으로만 답하세요.
{{
  "corrected": "교정된 텍스트",
  "explanation": "주요 개선점 설명"
}}"""

    try:
        return await call_openai(prompt, body.history or None)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="AI 응답 시간이 초과되었습니다.")
    except (json.JSONDecodeError, KeyError):
        raise HTTPException(status_code=500, detail="AI 응답 파싱에 실패했습니다.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
