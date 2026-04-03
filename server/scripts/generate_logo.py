"""Generate logo and app icon for Madaminu."""

import asyncio
import base64
import os
from pathlib import Path

from openai import AsyncOpenAI


LOGO_PROMPT = (
    "A dark, atmospheric logo for a murder mystery mobile game called 'Madaminu'. "
    "Multiple shadowy silhouettes of people standing in a circle, each casting long dramatic shadows. "
    "One silhouette holds a magnifying glass, another looks suspicious. "
    "Dark navy/black background with deep red and gold accents. "
    "Moody lighting from above creates mystery. "
    "The scene suggests a group of people playing a detective game together. "
    "Cinematic, noir-inspired illustration style. "
    "No text, no letters, no words anywhere in the image."
)

ICON_PROMPT = (
    "A square app icon for a murder mystery game. "
    "A dramatic composition: a magnifying glass over overlapping silhouettes of multiple people in shadow. "
    "Dark navy background with deep red accent lighting. "
    "Noir-inspired, moody atmosphere. Simple and recognizable at small sizes. "
    "No text, no letters, no words anywhere in the image."
)


async def generate_image(client: AsyncOpenAI, prompt: str, filename: str):
    print(f"Generating {filename}...")
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
            raise ValueError("No image data returned")

    output_dir = Path(__file__).parent.parent.parent / "assets"
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / filename
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(image_b64))

    print(f"Saved to {output_path}")
    return output_path


async def main():
    api_key = os.environ.get("MADAMINU_OPENAI_API_KEY")
    if not api_key:
        print("Set MADAMINU_OPENAI_API_KEY environment variable")
        return

    client = AsyncOpenAI(api_key=api_key)

    await generate_image(client, LOGO_PROMPT, "logo.png")
    await generate_image(client, ICON_PROMPT, "icon.png")
    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
