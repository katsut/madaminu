from madaminu.llm.client import LLMUsage
from madaminu.llm.prompts import format_characters_for_prompt, render_template


def test_llm_usage_cost_mini():
    usage = LLMUsage(model="gpt-5.4-mini", input_tokens=1000, output_tokens=500, duration_ms=2000)
    assert usage.estimated_cost_usd > 0
    assert "mini" in repr(usage)


def test_llm_usage_cost_nano():
    usage = LLMUsage(model="gpt-5.4-nano", input_tokens=1000, output_tokens=500, duration_ms=1000)
    assert usage.estimated_cost_usd > 0
    assert (
        usage.estimated_cost_usd
        < LLMUsage(model="gpt-5.4-mini", input_tokens=1000, output_tokens=500, duration_ms=1000).estimated_cost_usd
    )


def test_render_template():
    text = render_template("scenario_generate", characters="Alice, Bob")
    assert "Alice, Bob" in text
    assert "investigation" in text


def test_format_characters():
    chars = [
        {"character_name": "Detective", "character_personality": "Smart", "character_background": "Ex-cop"},
        {"character_name": "Doctor", "character_personality": "Kind", "character_background": "Surgeon"},
    ]
    result = format_characters_for_prompt(chars)
    assert "Detective" in result
    assert "Doctor" in result
    assert "Player 1" in result
    assert "Player 2" in result


def test_template_files_exist():
    from pathlib import Path

    templates_dir = Path(__file__).parent.parent / "src" / "madaminu" / "templates"
    assert (templates_dir / "scenario_system.txt").exists()
    assert (templates_dir / "scenario_generate.txt").exists()
    assert (templates_dir / "scenario_validate.txt").exists()
