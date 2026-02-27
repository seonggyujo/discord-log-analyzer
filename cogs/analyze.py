"""디버그 로그 분석 Cog - 텍스트 메시지 및 파일 첨부 지원"""

from __future__ import annotations

import os
from collections import defaultdict, deque
from time import time

import aiohttp  # type: ignore
import discord  # type: ignore
from discord.ext import commands, tasks  # type: ignore

from core.api import GroqClient
from core.config import (
    ALLOWED_EXTENSIONS,
    COOLDOWN_SECONDS,
    MAX_ATTACHMENT_SIZE,
    MAX_CONTEXT,
    MAX_MESSAGE_LENGTH,
    SYSTEM_PROMPT,
    logger,
)


class AnalyzeCog(commands.Cog):
    """디버그 로그 분석 기능을 담당하는 Cog.

    - 멘션(@봇) 및 !analyze 명령어로 로그 분석
    - 텍스트 메시지 및 파일 첨부(.log, .txt 등) 지원
    - 채널별 대화 컨텍스트 유지 (최근 10개)
    - 채널별 쿨타임 (3초)
    - 비활성 채널 자동 정리 (1시간)
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api = GroqClient()
        self.conversation_history: defaultdict[int, deque[dict[str, str]]] = (
            defaultdict(lambda: deque(maxlen=MAX_CONTEXT))
        )
        self.last_request_time: defaultdict[int, float] = defaultdict(float)

    async def cog_load(self) -> None:
        """Cog 로드 시 호출 - API 세션 시작 및 정리 태스크 시작"""
        await self.api.start()
        self.cleanup_inactive.start()

    async def cog_unload(self) -> None:
        """Cog 언로드 시 호출 - 리소스 정리"""
        self.cleanup_inactive.cancel()
        await self.api.close()

    # --- 유틸리티 ---

    def check_cooldown(self, channel_id: int) -> tuple[bool, float]:
        """쿨타임 확인. (통과여부, 남은시간) 반환."""
        current_time = time()
        elapsed = current_time - self.last_request_time[channel_id]

        if elapsed < COOLDOWN_SECONDS:
            return False, COOLDOWN_SECONDS - elapsed

        self.last_request_time[channel_id] = current_time
        return True, 0.0

    @staticmethod
    def split_message(
        text: str, max_length: int = MAX_MESSAGE_LENGTH
    ) -> list[str]:
        """긴 메시지를 Discord 제한(2000자)에 맞게 분할."""
        if len(text) <= max_length:
            return [text]

        chunks: list[str] = []
        while text:
            if len(text) <= max_length:
                chunks.append(text)
                break

            # 줄바꿈 또는 공백에서 분할
            split_index = text.rfind("\n", 0, max_length)
            if split_index == -1:
                split_index = text.rfind(" ", 0, max_length)
            if split_index == -1:
                split_index = max_length

            chunks.append(text[:split_index])
            text = text[split_index:].lstrip()

        return chunks

    @staticmethod
    async def read_attachment(attachment: discord.Attachment) -> tuple[str | None, str | None]:
        """Discord 첨부파일을 읽습니다.

        Returns:
            (파일 내용, None) - 성공 시
            (None, 에러 메시지) - 실패 시
        """
        # 파일 크기 검사
        if attachment.size > MAX_ATTACHMENT_SIZE:
            size_kb = attachment.size // 1024
            max_kb = MAX_ATTACHMENT_SIZE // 1024
            return None, f"파일이 너무 큽니다 ({size_kb}KB). 최대 {max_kb}KB까지 지원합니다."

        # 확장자 검사
        _, ext = os.path.splitext(attachment.filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            return None, (
                f"지원하지 않는 파일 형식입니다: `{ext}`\n"
                f"지원 형식: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )

        try:
            file_bytes = await attachment.read()
            content = file_bytes.decode("utf-8", errors="replace")
            return content, None
        except Exception as e:
            logger.error("첨부파일 읽기 오류: %s", e)
            return None, "파일을 읽는 중 오류가 발생했습니다."

    # --- 핵심 로직 ---

    async def process_message(
        self, message: discord.Message, content: str
    ) -> None:
        """공통 메시지 처리 로직."""
        channel_id = message.channel.id

        # 쿨타임 체크
        can_proceed, remaining = self.check_cooldown(channel_id)
        if not can_proceed:
            await message.reply(
                f"잠시만요! {remaining:.1f}초 후에 다시 시도해주세요."
            )
            return

        # 첨부파일 처리
        attachment_contents: list[str] = []
        for attachment in message.attachments:
            file_content, error = await self.read_attachment(attachment)
            if error:
                await message.reply(error)
                return
            attachment_contents.append(
                f"--- 파일: {attachment.filename} ---\n{file_content}"
            )

        # 최종 입력 구성
        full_content = content
        if attachment_contents:
            files_text = "\n\n".join(attachment_contents)
            if content:
                full_content = f"{content}\n\n{files_text}"
            else:
                full_content = files_text

        if not full_content.strip():
            await message.reply(
                "분석할 로그를 입력하거나 파일을 첨부해주세요!\n"
                "예: `!analyze 에러 로그 내용` 또는 `.log` 파일 첨부"
            )
            return

        # 컨텍스트에 메시지 추가
        self.conversation_history[channel_id].append(
            {"role": "user", "content": full_content}
        )

        # API 요청 메시지 구성
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *list(self.conversation_history[channel_id]),
        ]

        # API 호출 (입력 중 표시)
        async with message.channel.typing():
            response, error = await self.api.chat(messages)

        if error:
            # 실패 시 컨텍스트에서 제거
            self.conversation_history[channel_id].pop()
            await message.reply(error)
            return

        # 성공 시 어시스턴트 응답도 컨텍스트에 저장
        self.conversation_history[channel_id].append(
            {"role": "assistant", "content": response}
        )

        # 메시지 분할 전송
        chunks = self.split_message(response)
        for i, chunk in enumerate(chunks):
            if i == 0:
                await message.reply(chunk)
            else:
                await message.channel.send(chunk)

    # --- 이벤트 리스너 ---

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """멘션(@봇) 기반 메시지 처리 - 텍스트 및 파일 첨부 지원."""
        if message.author.bot:
            return

        if not self.bot.user.mentioned_in(message):
            return

        # @everyone, @here 멘션 제외
        if message.mention_everyone:
            return

        content = (
            message.content.replace(f"<@{self.bot.user.id}>", "")
            .replace(f"<@!{self.bot.user.id}>", "")
            .strip()
        )

        # 텍스트 또는 첨부파일이 있으면 처리
        if content or message.attachments:
            await self.process_message(message, content)
        else:
            await message.reply(
                "분석할 로그를 입력하거나 파일을 첨부해주세요!\n"
                "예: `@봇이름 에러 로그 내용` 또는 `.log` 파일 첨부"
            )

    # --- 명령어 ---

    @commands.command(name="analyze", aliases=["분석", "log", "debug"])
    async def analyze_command(
        self, ctx: commands.Context, *, message: str = ""
    ) -> None:
        """로그를 분석하는 명령어.

        사용법:
          !analyze <에러 로그>
          !분석 <에러 로그>
          !log <에러 로그>
          !debug <에러 로그>
          또는 파일을 첨부하여 !analyze
        """
        if not message and not ctx.message.attachments:
            await ctx.reply(
                "분석할 로그를 입력하거나 파일을 첨부해주세요!\n"
                "예: `!analyze 에러 로그 내용`\n"
                "또는 `.log` / `.txt` 파일을 첨부하여 `!analyze`"
            )
            return
        await self.process_message(ctx.message, message)

    @commands.command(name="chat", aliases=["채팅"])
    async def chat_command(
        self, ctx: commands.Context, *, message: str = ""
    ) -> None:
        """일반 채팅 명령어.

        사용법:
          !chat <메시지>
          !채팅 <메시지>
        """
        if not message:
            await ctx.reply("메시지를 입력해주세요! 예: `!chat 안녕하세요`")
            return
        await self.process_message(ctx.message, message)

    @commands.command(name="clear", aliases=["초기화"])
    async def clear_command(self, ctx: commands.Context) -> None:
        """현재 채널의 대화 기록을 초기화합니다."""
        channel_id = ctx.channel.id
        if channel_id in self.conversation_history:
            self.conversation_history.pop(channel_id)
            await ctx.reply("대화 기록이 초기화되었습니다.")
        else:
            await ctx.reply("초기화할 대화 기록이 없습니다.")

    # --- 주기적 태스크 ---

    @tasks.loop(hours=1)
    async def cleanup_inactive(self) -> None:
        """1시간 이상 비활성 채널의 대화 데이터를 정리합니다."""
        current = time()
        inactive = [
            ch_id
            for ch_id, last_time in self.last_request_time.items()
            if current - last_time > 3600
        ]
        for ch_id in inactive:
            self.conversation_history.pop(ch_id, None)
            self.last_request_time.pop(ch_id, None)
        if inactive:
            logger.info("비활성 채널 %d개 정리 완료", len(inactive))

    @cleanup_inactive.before_loop
    async def before_cleanup(self) -> None:
        """봇이 준비될 때까지 정리 태스크 대기."""
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    """Cog을 봇에 등록합니다."""
    await bot.add_cog(AnalyzeCog(bot))
