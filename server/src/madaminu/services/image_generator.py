import base64
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


async def generate_character_portrait(
    client: AsyncOpenAI,
    character_name: str,
    personality: str,
    background: str,
) -> str:
    prompt = (
        f"A stylized portrait of a character named {character_name} for a murder mystery game. "
        f"Personality: {personality}. Background: {background}. "
        "Dark, moody atmosphere with dramatic lighting. Semi-realistic illustration style."
    )

    response = await client.images.generate(
        model="gpt-image-1-mini",
        prompt=prompt,
        size="1024x1024",
        quality="low",
        n=1,
    )

    image_b64 = response.data[0].b64_json
    if image_b64 is None:
        url = response.data[0].url
        if url:
            import httpx

            async with httpx.AsyncClient() as http:
                resp = await http.get(url)
                resp.raise_for_status()
                image_b64 = base64.b64encode(resp.content).decode()
        else:
            raise ValueError("No image data returned from API")

    return image_b64


async def generate_scene_image(
    client: AsyncOpenAI,
    setting_description: str,
) -> str:
    prompt = (
        f"A wide establishing shot of a murder mystery scene: {setting_description}. "
        "Dark, atmospheric, cinematic composition. Detailed environment illustration."
    )

    response = await client.images.generate(
        model="gpt-image-1-mini",
        prompt=prompt,
        size="1024x1024",
        quality="low",
        n=1,
    )

    image_b64 = response.data[0].b64_json
    if image_b64 is None:
        url = response.data[0].url
        if url:
            import httpx

            async with httpx.AsyncClient() as http:
                resp = await http.get(url)
                resp.raise_for_status()
                image_b64 = base64.b64encode(resp.content).decode()
        else:
            raise ValueError("No image data returned from API")

    return image_b64

async def generate_victim_portrait(
    client: AsyncOpenAI,
    victim_name: str,
    victim_description: str,
) -> str:
    prompt = (
        f"A portrait of a murder victim named {victim_name} for a mystery game. "
        f"Description: {victim_description}. "
        "Somber, memorial-style portrait. Semi-realistic illustration."
    )

    response = await client.images.generate(
        model="gpt-image-1-mini",
        prompt=prompt,
        size="1024x1024",
        quality="low",
        n=1,
    )

    image_b64 = response.data[0].b64_json
    if image_b64 is None:
        url = response.data[0].url
        if url:
            import httpx

            async with httpx.AsyncClient() as http:
                resp = await http.get(url)
                resp.raise_for_status()
                image_b64 = base64.b64encode(resp.content).decode()
        else:
            raise ValueError("No image data returned from API")

    return image_b64
