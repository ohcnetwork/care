import json
import logging

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

SOAP_SYSTEM_PROMPT = """You are a medical documentation assistant specializing in 
clinical note generation. You convert medical conversation transcripts into structured 
SOAP (Subjective, Objective, Assessment, Plan) notes.

Rules:
- Extract only factual information present in the transcript.
- Do NOT hallucinate or infer information not explicitly stated.
- If a SOAP section has no relevant information, write "Not documented in this encounter."
- Use standard medical terminology.
- Be concise but thorough.
- Identify and separate provider statements from patient statements when possible.
"""

SOAP_USER_PROMPT_TEMPLATE = """Convert the following medical conversation transcript into 
a structured SOAP note. Return ONLY valid JSON with these exact keys:
{{
  "subjective": "Patient's reported symptoms, history, and concerns",
  "objective": "Clinical findings, vital signs, examination results",
  "assessment": "Clinical assessment, differential diagnoses, impressions",
  "plan": "Treatment plan, medications, follow-up instructions",
  "summary": "A 2-3 sentence clinical summary of the encounter"
}}

Transcript:
---
{transcript}
---

Generate the SOAP note as JSON:"""


def get_llm_config() -> dict:
    """Get LLM configuration from plugin settings."""
    plugin_configs = getattr(settings, "PLUGIN_CONFIGS", {})
    ai_voice_config = plugin_configs.get("ai_voice", {})
    return {
        "api_key": ai_voice_config.get(
            "OPENAI_API_KEY",
            getattr(settings, "OPENAI_API_KEY", ""),
        ),
        "model": ai_voice_config.get(
            "LLM_MODEL",
            getattr(settings, "AI_VOICE_LLM_MODEL", "gpt-4o"),
        ),
        "temperature": float(
            ai_voice_config.get(
                "LLM_TEMPERATURE",
                getattr(settings, "AI_VOICE_LLM_TEMPERATURE", 0.2),
            )
        ),
        "base_url": ai_voice_config.get(
            "OPENAI_BASE_URL",
            getattr(settings, "AI_VOICE_OPENAI_BASE_URL", None),
        ),
    }


def generate_soap_from_transcript(transcript: str) -> dict:
    """Generate a SOAP note from a medical conversation transcript.

    Returns dict with keys: subjective, objective, assessment, plan, summary,
    plus metadata in 'meta'.
    """
    config = get_llm_config()
    if not config["api_key"]:
        raise ValueError("OpenAI API key is not configured for ai_voice plugin")

    client_kwargs = {"api_key": config["api_key"]}
    if config["base_url"]:
        client_kwargs["base_url"] = config["base_url"]

    client = OpenAI(**client_kwargs)

    user_prompt = SOAP_USER_PROMPT_TEMPLATE.format(transcript=transcript)

    response = client.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "system", "content": SOAP_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=config["temperature"],
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    content = response.choices[0].message.content
    usage = response.usage

    try:
        soap_data = json.loads(content)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM response as JSON: %s", content[:500])
        raise ValueError("LLM returned invalid JSON response")

    return {
        "subjective": soap_data.get("subjective", ""),
        "objective": soap_data.get("objective", ""),
        "assessment": soap_data.get("assessment", ""),
        "plan": soap_data.get("plan", ""),
        "summary": soap_data.get("summary", ""),
        "meta": {
            "model": config["model"],
            "temperature": config["temperature"],
            "input_tokens": usage.prompt_tokens if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        },
    }
