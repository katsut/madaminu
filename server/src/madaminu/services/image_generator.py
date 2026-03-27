import base64
import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


async def generate_character_portrait(
    client: AsyncOpenAI,
    gender: str,
    age: str,
    appearance: str,
) -> str:
    gender_desc = {"男": "male", "女": "female"}.get(gender, "")
    age_desc = f"{age} years old" if age and age != "不明" else ""
    appearance_desc = appearance if appearance else ""

    subject = " ".join(filter(None, [age_desc, gender_desc])) or "character"

    prompt = (
        f"A portrait of a {subject} for a mystery game. "
        f"{appearance_desc} "
        "Clean, well-lit background with soft gradient. "
        "Clear facial features and distinctive appearance visible. "
        "Semi-realistic illustration style, warm lighting on the face. "
        "Show face and upper body. "
        "The character can be human, animal, robot, or any creature. "
        "Absolutely no text, no labels, no names, no words, no letters anywhere in the image."
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
        "Dark, atmospheric, cinematic composition. Detailed environment illustration. "
        "No text, no labels, no names, no words in the image. Scene only."
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
        f"A portrait of a murder victim for a mystery game. "
        f"Description: {victim_description}. "
        "Somber, memorial-style portrait. Semi-realistic illustration. "
        "No text, no labels, no names, no words in the image. Portrait only."
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
