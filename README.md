# Discord Debug Log Analyzer Bot

Discord에서 디버그 로그를 분석하고 일반 대화도 가능한 AI 챗봇

## 기능

| 명령어 | 설명 |
|--------|------|
| `!analyze <로그>` | 디버그 로그 분석 (별칭: `!분석`, `!log`, `!debug`) |
| `!chat <메시지>` | 일반 대화 (별칭: `!채팅`) |
| `!clear` | 대화 기록 초기화 (별칭: `!초기화`) |
| `!info` | 봇 정보 표시 |
| `@봇멘션 <메시지>` | 멘션으로 분석 또는 대화 |

파일 첨부도 지원 (`.log`, `.txt`, `.json`, `.py` 등 최대 512KB)

## 특징

- 채널별 최근 10개 메시지 컨텍스트 유지
- 채널별 3초 쿨타임
- 1시간 비활성 채널 자동 정리
- 2000자 초과 시 자동 분할 전송
- API 재시도 (최대 3회) 및 Rate Limit 처리
- 금지 키워드 필터링 (코드 + 프롬프트 이중 방어)

## 기술 스택

| 구분 | 기술 |
|------|------|
| Runtime | Python 3.10 |
| Discord | discord.py >=2.3.0 |
| HTTP | aiohttp >=3.9.0 |
| AI API | Groq API (openai/gpt-oss-120b) |

## 프로젝트 구조

```
├── bot.py                  # 메인 진입점
├── cogs/
│   ├── analyze.py          # 로그 분석 Cog (핵심 기능)
│   └── info.py             # 봇 정보 Cog
├── core/
│   ├── api.py              # Groq API 클라이언트
│   └── config.py           # 설정, 상수, 시스템 프롬프트
├── requirements.txt        # 의존성
├── .env.example            # 환경변수 템플릿
└── log-analyzer-bot.service # systemd 서비스 파일
```

## 설치

```bash
git clone https://github.com/seonggyujo/discord-log-analyzer.git
cd discord-log-analyzer
pip install -r requirements.txt
```

## 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 값 입력:

```
DISCORD_BOT_TOKEN=your_discord_bot_token_here
GROQ_API_KEY=your_groq_api_key_here
```

## 실행

```bash
python bot.py
```

## 서버 배포 (systemd)

```bash
sudo cp log-analyzer-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable log-analyzer-bot
sudo systemctl start log-analyzer-bot
```
