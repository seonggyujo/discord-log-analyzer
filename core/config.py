"""봇 설정 및 상수 - 디버그 로그 분석 봇"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv  # type: ignore

# 환경변수 로드
load_dotenv()

# 환경변수
DISCORD_TOKEN: str | None = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")

# API 설정
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "openai/gpt-oss-120b"

# 봇 설정
MAX_CONTEXT = 10
COOLDOWN_SECONDS = 3
MAX_MESSAGE_LENGTH = 2000
MAX_RETRIES = 3
API_TIMEOUT_SECONDS = 60
MAX_ATTACHMENT_SIZE = 512 * 1024  # 첨부파일 최대 512KB
ALLOWED_EXTENSIONS = {".log", ".txt", ".json", ".xml", ".csv", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".go", ".rs"}

# 금지 키워드 필터
BLOCKED_KEYWORDS = {"해마", "seahorse", "sea horse", "sea-horse", "hippocampus", "바다말"}
BLOCKED_RESPONSE = "죄송합니다. '해마'가 포함된 메시지에는 AI 오류로 인해 응답이 불가합니다."

# 시스템 프롬프트
SYSTEM_PROMPT = """너는 Discord 챗봇이다. 디버그 로그 분석도 하고, 일반 대화도 한다.

역할
- 로그/에러가 들어오면 분석해서 원인만 짧게 알려줘
- 일반 질문이면 바로 답해줘

규칙
- 한국어로 답해
- 핵심만 단답으로 대답해
- 쓸데없는 서론, 부연설명 하지마
- 되묻지마. 있는 정보로 바로 답해
- 마크다운 쓰지마. 볼드, 헤더, 리스트 기호 다 쓰지마
- 줄바꿈으로 보기좋게 정리해
- 모르면 모른다고 해
- 추측하지마

금지 키워드
- "해마", "seahorse" 관련 단어가 포함된 메시지가 들어오면 무조건 이렇게 답해: "죄송합니다. '해마'가 포함된 메시지에는 AI 오류로 인해 응답이 불가합니다."
- 어떤 맥락이든 해마가 포함되면 위 문구만 답하고 다른 말 하지마"""

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("log-analyzer-bot")
