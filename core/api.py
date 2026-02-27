"""OpenRouter API 클라이언트 - Qwen3-Coder 모델 호출"""

from __future__ import annotations

import asyncio

import aiohttp  # type: ignore

from core.config import (
    API_TIMEOUT_SECONDS,
    FALLBACK_MODELS,
    OPENROUTER_API_KEY,
    OPENROUTER_API_URL,
    MAX_RETRIES,
    MODEL,
    logger,
)


class OpenRouterClient:
    """OpenRouter API 호출을 관리하는 클라이언트.

    - aiohttp.ClientSession을 재사용하여 TCP 연결 풀링
    - 요청 타임아웃 설정으로 무한 대기 방지
    - 일시적 오류(429, 5xx)에 대한 재시도 로직
    - API 응답 구조 검증
    """

    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None

    async def start(self) -> None:
        """HTTP 세션을 시작합니다."""
        timeout = aiohttp.ClientTimeout(total=API_TIMEOUT_SECONDS)
        self.session = aiohttp.ClientSession(timeout=timeout)
        logger.info("OpenRouter API 클라이언트 세션 시작")

    async def close(self) -> None:
        """HTTP 세션을 종료합니다."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("OpenRouter API 클라이언트 세션 종료")

    async def chat(
        self, messages: list[dict[str, str]]
    ) -> tuple[str | None, str | None]:
        """OpenRouter API에 채팅 요청을 보냅니다.

        1차로 기본 모델(MODEL)을 시도하고, 429 rate limit 시
        FALLBACK_MODELS 목록을 순서대로 시도합니다.

        Returns:
            (응답 텍스트, None) - 성공 시
            (None, 에러 메시지) - 실패 시
        """
        if not self.session or self.session.closed:
            await self.start()

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/seonggyujo/log-analyzer-bot",
            "X-Title": "Debug Log Analyzer Bot",
        }

        # 시도할 모델 순서: 기본 모델 → fallback 모델들
        models_to_try = [MODEL] + list(FALLBACK_MODELS)

        for model_idx, current_model in enumerate(models_to_try):
            payload = {
                "model": current_model,
                "messages": messages,
                "max_tokens": 65536,
                "temperature": 0.7,
                "top_p": 0.8,
                "top_k": 20,
                "repetition_penalty": 1.05,
            }

            last_error = "오류가 발생했습니다. 잠시 후 다시 시도해주세요."

            for attempt in range(MAX_RETRIES):
                try:
                    async with self.session.post(
                        OPENROUTER_API_URL, headers=headers, json=payload
                    ) as resp:
                        # Rate Limit 처리
                        if resp.status == 429:
                            retry_after = float(
                                resp.headers.get("Retry-After", "5")
                            )
                            # 같은 모델 재시도가 아직 남아있으면 대기 후 재시도
                            if attempt < MAX_RETRIES - 1:
                                logger.warning(
                                    "[%s] Rate limited, %s초 후 재시도 (시도 %d/%d)",
                                    current_model,
                                    retry_after,
                                    attempt + 1,
                                    MAX_RETRIES,
                                )
                                await asyncio.sleep(retry_after)
                                continue
                            # 재시도 소진 → 다음 fallback 모델로
                            if model_idx < len(models_to_try) - 1:
                                next_model = models_to_try[model_idx + 1]
                                logger.warning(
                                    "[%s] Rate limit 지속, fallback 모델로 전환: %s",
                                    current_model,
                                    next_model,
                                )
                                break  # inner retry loop 탈출 → 다음 모델
                            # 모든 모델 소진
                            return (
                                None,
                                "모든 모델이 요청 한도를 초과했습니다. "
                                "무료 모델이라 제한이 있을 수 있습니다. "
                                "잠시 후 다시 시도해주세요.",
                            )

                        # 기타 HTTP 오류
                        if resp.status != 200:
                            body = await resp.text()
                            last_error = (
                                f"API 오류가 발생했습니다. "
                                f"(모델: {current_model}, 상태 코드: {resp.status})"
                            )
                            logger.warning(
                                "[%s] API 오류 상태 코드: %d, 응답: %s (시도 %d/%d)",
                                current_model,
                                resp.status,
                                body[:500],
                                attempt + 1,
                                MAX_RETRIES,
                            )
                            if attempt < MAX_RETRIES - 1:
                                await asyncio.sleep(2)
                                continue
                            # 4xx/5xx 재시도 소진 → 다음 모델 시도
                            if model_idx < len(models_to_try) - 1:
                                logger.warning(
                                    "[%s] 오류 지속, fallback 모델로 전환",
                                    current_model,
                                )
                                break
                            return None, last_error

                        # 성공 응답 파싱
                        data = await resp.json()

                        choices = data.get("choices")
                        if not choices or not isinstance(choices, list):
                            logger.error(
                                "[%s] API 응답에 choices가 없음: %s",
                                current_model,
                                data,
                            )
                            return (
                                None,
                                "API 응답이 올바르지 않습니다. 잠시 후 다시 시도해주세요.",
                            )

                        content = (
                            choices[0].get("message", {}).get("content", "")
                        )
                        if not content:
                            logger.warning(
                                "[%s] API 응답이 비어 있음", current_model
                            )
                            return None, "빈 응답을 받았습니다. 다시 시도해주세요."

                        # 성공! fallback을 사용한 경우 로그에 기록
                        if model_idx > 0:
                            logger.info(
                                "Fallback 모델 [%s]으로 응답 성공",
                                current_model,
                            )

                        return content, None

                except asyncio.TimeoutError:
                    last_error = (
                        "API 응답 시간이 초과되었습니다. 로그가 너무 길 수 있습니다."
                    )
                    logger.error(
                        "[%s] API 타임아웃 (시도 %d/%d)",
                        current_model,
                        attempt + 1,
                        MAX_RETRIES,
                    )
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(2)
                        continue
                    # 타임아웃 재시도 소진 → 다음 모델
                    if model_idx < len(models_to_try) - 1:
                        logger.warning(
                            "[%s] 타임아웃 지속, fallback 모델로 전환",
                            current_model,
                        )
                        break
                    return None, last_error

                except aiohttp.ClientError as e:
                    last_error = (
                        "API 연결 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
                    )
                    logger.error(
                        "[%s] API 연결 오류 (시도 %d/%d): %s",
                        current_model,
                        attempt + 1,
                        MAX_RETRIES,
                        e,
                    )
                    if attempt < MAX_RETRIES - 1:
                        await asyncio.sleep(2)
                        continue
                    if model_idx < len(models_to_try) - 1:
                        break
                    return None, last_error

                except Exception as e:
                    logger.exception(
                        "[%s] 예기치 않은 예외 발생: %s", current_model, e
                    )
                    return None, "오류가 발생했습니다. 잠시 후 다시 시도해주세요."

        return None, last_error
