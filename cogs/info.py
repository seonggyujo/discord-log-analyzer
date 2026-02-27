"""봇 정보 명령어 Cog"""

from __future__ import annotations

from discord.ext import commands  # type: ignore

from core.config import MODEL


class InfoCog(commands.Cog):
    """봇 정보를 표시하는 Cog."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command(name="info")
    async def info_command(self, ctx: commands.Context) -> None:
        """봇 정보 표시."""
        info_text = f"""**[Debug Log Analyzer Bot]**
**모델**: `{MODEL}`
**API**: OpenRouter (무료 티어)
**기능**: 디버그 로그 분석, 에러 추적, 코드 디버깅

**사용법:**
- `!analyze <로그>` - 로그 분석
- `!분석 <로그>` - 로그 분석 (한글 별칭)
- `!log <로그>` - 로그 분석 (별칭)
- `!debug <로그>` - 디버그 분석 (별칭)
- `!clear` - 대화 기록 초기화
- `@봇이름 <로그>` - 멘션으로 분석
- 파일 첨부 (`.log`, `.txt` 등) 지원

**개발자**: seonggyujo
**GitHub**: https://github.com/seonggyujo"""
        await ctx.reply(info_text)


async def setup(bot: commands.Bot) -> None:
    """Cog을 봇에 등록합니다."""
    await bot.add_cog(InfoCog(bot))
