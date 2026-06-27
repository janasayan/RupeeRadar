"""Groq LLM client — used from Phase 2 onward for categorization and insights.

Rate limits for llama-3.3-70b-versatile (free tier):
  - 30 requests / minute
  - 1,000 tokens / minute
  - 12,000 requests / day
  - 100,000 tokens / day
"""

from __future__ import annotations

import logging
import time
from collections import deque

from groq import Groq

from app.config.settings import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------

_RPM_LIMIT = 30
_TPM_LIMIT = 1_000
_RPD_LIMIT = 12_000
_TPD_LIMIT = 100_000

_WINDOW_MINUTE = 60.0   # seconds
_WINDOW_DAY = 86_400.0  # seconds


class _RateLimiter:
    """Sliding-window rate limiter tracking RPM / TPM / RPD / TPD."""

    def __init__(self) -> None:
        # Each entry: (timestamp, token_count)
        self._minute_calls: deque[tuple[float, int]] = deque()
        self._day_calls: deque[tuple[float, int]] = deque()

    def _evict(self, q: deque[tuple[float, int]], window: float, now: float) -> None:
        cutoff = now - window
        while q and q[0][0] < cutoff:
            q.popleft()

    def acquire(self, estimated_tokens: int) -> None:
        """Block until within all four rate limits, then record the call."""
        while True:
            now = time.monotonic()
            self._evict(self._minute_calls, _WINDOW_MINUTE, now)
            self._evict(self._day_calls, _WINDOW_DAY, now)

            rpm = len(self._minute_calls)
            tpm = sum(t for _, t in self._minute_calls)
            rpd = len(self._day_calls)
            tpd = sum(t for _, t in self._day_calls)

            if rpm >= _RPM_LIMIT:
                # Wait until the oldest minute-window call expires
                sleep_s = (_WINDOW_MINUTE - (now - self._minute_calls[0][0])) + 0.05
                logger.debug("RPM limit hit — sleeping %.1fs", sleep_s)
                time.sleep(max(sleep_s, 0.05))
                continue

            if tpm + estimated_tokens > _TPM_LIMIT:
                sleep_s = (_WINDOW_MINUTE - (now - self._minute_calls[0][0])) + 0.05 if self._minute_calls else 1.0
                logger.debug("TPM limit hit — sleeping %.1fs", sleep_s)
                time.sleep(max(sleep_s, 0.05))
                continue

            if rpd >= _RPD_LIMIT:
                raise RuntimeError(f"Groq daily request limit ({_RPD_LIMIT} RPD) reached.")

            if tpd + estimated_tokens > _TPD_LIMIT:
                raise RuntimeError(f"Groq daily token limit ({_TPD_LIMIT} TPD) reached.")

            # All checks pass — record and proceed
            entry = (now, estimated_tokens)
            self._minute_calls.append(entry)
            self._day_calls.append(entry)
            return


_rate_limiter = _RateLimiter()


# ---------------------------------------------------------------------------
# LLM service
# ---------------------------------------------------------------------------


class GroqLLMService:
    def __init__(self) -> None:
        self._client: Groq | None = None
        if settings.llm_enabled:
            self._client = Groq(api_key=settings.groq_api_key)

    @property
    def available(self) -> bool:
        return self._client is not None

    @property
    def model(self) -> str:
        return settings.groq_model

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.2,
        estimated_tokens: int = 800,
    ) -> str:
        """Call the LLM, honouring rate limits before dispatching.

        ``estimated_tokens`` should be a conservative upper-bound for the
        combined input + output tokens so the limiter can account for them
        before the actual API call is made.  Defaults to 800 (safe for a
        batch of 10 transactions).
        """
        if not self._client:
            raise RuntimeError("Groq API key not configured. Set GROQ_API_KEY in .env")

        _rate_limiter.acquire(estimated_tokens)

        response = self._client.chat.completions.create(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Empty response from Groq")
        return content


llm_service = GroqLLMService()
