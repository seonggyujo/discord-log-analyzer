"""봇 설정 및 상수 - 디버그 로그 분석 봇"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv  # type: ignore

# 환경변수 로드
load_dotenv()

# 환경변수
DISCORD_TOKEN: str | None = os.getenv("DISCORD_BOT_TOKEN")
OPENROUTER_API_KEY: str | None = os.getenv("OPENROUTER_API_KEY")

# API 설정
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
MODEL = "qwen/qwen3-coder:free"

# Fallback 모델 목록 (1순위가 rate limit 시 순서대로 시도)
FALLBACK_MODELS = [
    "deepseek/deepseek-chat-v3-0324:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

# 봇 설정
MAX_CONTEXT = 10
COOLDOWN_SECONDS = 3
MAX_MESSAGE_LENGTH = 2000
MAX_RETRIES = 3
API_TIMEOUT_SECONDS = 120  # Qwen3-Coder는 긴 응답 생성 가능
MAX_ATTACHMENT_SIZE = 512 * 1024  # 첨부파일 최대 512KB
ALLOWED_EXTENSIONS = {".log", ".txt", ".json", ".xml", ".csv", ".yaml", ".yml", ".ini", ".cfg", ".conf", ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".go", ".rs"}

# 시스템 프롬프트 - 디버그 로그 분석 전문가
SYSTEM_PROMPT = """You are a professional debug log analyst assistant running on Discord.
Your role is to analyze debug logs, error traces, and system outputs that users provide.

## Core Responsibilities
1. **Root Cause Analysis**: Identify the root cause of errors from logs
2. **Error Classification**: Classify error severity (CRITICAL / ERROR / WARNING / INFO)
3. **Solution Suggestions**: Provide actionable fix suggestions
4. **Pattern Recognition**: Detect recurring error patterns and anomalies

## Response Format
Structure your analysis as follows:

### Summary
- Brief one-line summary of the issue

### Error Analysis
- Identify the specific error(s) and their locations
- Explain what each error means

### Root Cause
- Explain the likely root cause

### Recommended Fix
- Provide concrete, actionable steps to resolve the issue
- Include code snippets if applicable

### Additional Notes
- Any warnings, performance concerns, or preventive measures

## Rules
- Respond in Korean (한국어) unless the user explicitly asks for English
- Be concise but thorough
- If the log is incomplete or ambiguous, state what additional information would help
- Do not guess or fabricate information - if uncertain, say so
- When analyzing code, point out the exact line/section causing the issue
- Format responses with Discord markdown (```code blocks```, **bold**, etc.)
- If the input is not a log/error but a general question, still respond helpfully"""

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("log-analyzer-bot")
