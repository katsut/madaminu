"""Generate logo and app icon via ComfyUI."""

import json
import time
import urllib.request
import shutil
from pathlib import Path

COMFYUI_URL = "http://127.0.0.1:8188"
OUTPUT_DIR = Path("/Users/tsuruta/Develop/private/ComfyUI/output")
ASSETS_DIR = Path("/Users/tsuruta/Develop/private/murder/assets")
ASSETS_DIR.mkdir(exist_ok=True)

LOGO_PROMPT = (
    "masterpiece, best quality, "
    "dark noir illustration, murder mystery game key art, "
    "group of 5 shadowy silhouettes standing in a circle around a dim spotlight on the floor, "
    "one figure holds a magnifying glass, another crosses their arms suspiciously, "
    "dramatic overhead lighting casting long shadows, "
    "dark navy and black background, deep crimson red accents, subtle gold highlights, "
    "atmospheric fog, cinematic composition, film noir style, "
    "moody detective game atmosphere, multiplayer group dynamic, "
    "wide composition for logo background"
)

ICON_PROMPT = (
    "masterpiece, best quality, "
    "dark noir app icon design, centered composition, "
    "a magnifying glass with 3 overlapping human silhouettes visible through the lens, "
    "dark navy background, deep red rim lighting, "
    "simple and bold, recognizable at small sizes, "
    "noir style, mystery atmosphere, square composition"
)

NEGATIVE = (
    "text, letters, words, watermark, signature, logo text, title, "
    "low quality, blurry, deformed, ugly, bad anatomy, "
    "bright colors, cheerful, cartoon, chibi"
)


def build_workflow(prompt_text, negative_text, width, height, seed, filename_prefix):
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 30,
                "cfg": 7.5,
                "sampler_name": "euler_ancestral",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt_text, "clip": ["4", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": negative_text, "clip": ["4", 1]},
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": filename_prefix, "images": ["8", 0]},
        },
    }


def queue_prompt(workflow):
    data = json.dumps({"prompt": workflow}).encode()
    req = urllib.request.Request(
        f"{COMFYUI_URL}/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def wait_for_completion(prompt_id):
    while True:
        req = urllib.request.Request(f"{COMFYUI_URL}/history/{prompt_id}")
        resp = urllib.request.urlopen(req)
        history = json.loads(resp.read())
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)


def find_output(history, filename_prefix):
    outputs = history.get("outputs", {})
    for node_id, node_output in outputs.items():
        images = node_output.get("images", [])
        for img in images:
            if img.get("filename", "").startswith(filename_prefix):
                return OUTPUT_DIR / img["filename"]
    return None


def generate(name, prompt, negative, width, height, seed):
    prefix = f"madaminu_{name}"
    print(f"Generating {name} ({width}x{height})...")
    workflow = build_workflow(prompt, negative, width, height, seed, prefix)
    result = queue_prompt(workflow)
    prompt_id = result["prompt_id"]
    print(f"  Queued: {prompt_id}")
    history = wait_for_completion(prompt_id)
    output_path = find_output(history, prefix)
    if output_path and output_path.exists():
        dest = ASSETS_DIR / f"{name}.png"
        shutil.copy2(output_path, dest)
        print(f"  Saved: {dest}")
    else:
        print(f"  ERROR: Output not found for {prefix}")


if __name__ == "__main__":
    generate("logo", LOGO_PROMPT, NEGATIVE, 1536, 768, seed=42)
    generate("icon", ICON_PROMPT, NEGATIVE, 1024, 1024, seed=123)
    print("Done!")
