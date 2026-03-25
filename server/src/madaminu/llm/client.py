import logging
import time

import anthropic

from madaminu.config import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"
HAIKU_MODEL = "claude-haiku-4-5-20251001"


class LLMUsage:
    def __init__(self, model: str, input_tokens: int, output_tokens: int, duration_ms: int):
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.duration_ms = duration_ms

    @property
    def estimated_cost_usd(self) -> float:
        if "sonnet" in self.model:
            return (self.input_tokens * 3.0 + self.output_tokens * 15.0) / 1_000_000
        if "haiku" in self.model:
            return (self.input_tokens * 0.8 + self.output_tokens * 4.0) / 1_000_000
        return 0.0

    def __repr__(self) -> str:
        return (
            f"LLMUsage(model={self.model}, in={self.input_tokens}, out={self.output_tokens}, "
            f"cost=${self.estimated_cost_usd:.4f}, duration={self.duration_ms}ms)"
        )


class LLMClient:
    def __init__(self):
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
    ) -> tuple[str, LLMUsage]:
        start = time.monotonic()

        response = await self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        text = response.content[0].text
        usage = LLMUsage(
            model=model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            duration_ms=duration_ms,
        )

        logger.info("LLM call: %s", usage)
        return text, usage

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
    ) -> tuple[str, LLMUsage]:
        system_with_json = system_prompt + "\n\nIMPORTANT: Respond with valid JSON only. No markdown, no code blocks."
        return await self.generate(system_with_json, user_prompt, model, max_tokens)


llm_client = LLMClient()
