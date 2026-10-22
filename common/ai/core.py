import json
from dataclasses import fields, is_dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from openai import OpenAI

OPENAI_MODEL_SMART = "gpt-6.1-sol"
OPENAI_MODEL_DUMB = "gpt-6-luna"


def openai_client():
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise ImproperlyConfigured("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key, timeout=45, max_retries=0)


def schema_from(cls):
    properties = {}
    for item in fields(cls):
        spec = dict(item.metadata)

        description = spec.pop("description", "")
        if "items" in spec and is_dataclass(spec["items"]):
            spec["type"] = "array"
            spec["items"] = schema_from(spec["items"])

        prop = {"type": spec.pop("type", "string"), **spec}
        if description:
            prop["description"] = description
        properties[item.name] = prop

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": properties,
        "required": list(properties),
    }


def ask_llm_structured(instructions, text, schema, model=OPENAI_MODEL_DUMB):
    response = openai_client().responses.create(
        model=model,
        reasoning={"effort": "low"},
        input=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": text},
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "result",
                "strict": True,
                "schema": schema,
            },
        },
    )
    raw = response.output_text
    if not raw:
        raise ValueError("Model returned no structured output")
    return json.loads(raw)
