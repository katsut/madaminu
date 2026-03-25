import logging
import time

from openai import AsyncOpenAI

from madaminu.config import settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-5.4-mini"
LIGHT_MODEL = "gpt-5.4-nano"


class LLMUsage:
    def __init__(self, model: str, input_tokens: int, output_tokens: int, duration_ms: int):
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.duration_ms = duration_ms

    @property
    def estimated_cost_usd(self) -> float:
        if "5.4-mini" in self.model:
            return (self.input_tokens * 0.4 + self.output_tokens * 1.6) / 1_000_000
        if "5.4-nano" in self.model:
            return (self.input_tokens * 0.1 + self.output_tokens * 0.4) / 1_000_000
        return 0.0

    def __repr__(self) -> str:
        return (
            f"LLMUsage(model={self.model}, in={self.input_tokens}, out={self.output_tokens}, "
            f"cost=${self.estimated_cost_usd:.4f}, duration={self.duration_ms}ms)"
        )


class LLMClient:
    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = DEFAULT_MODEL,
        max_tokens: int = 4096,
    ) -> tuple[str, LLMUsage]:
        start = time.monotonic()

        response = await self._client.chat.completions.create(
            model=model,
            max_completion_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        text = response.choices[0].message.content or ""
        usage = LLMUsage(
            model=model,
            input_tokens=response.usage.prompt_tokens if response.usage else 0,
            output_tokens=response.usage.completion_tokens if response.usage else 0,
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
