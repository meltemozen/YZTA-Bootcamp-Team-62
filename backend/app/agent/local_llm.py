"""Local LLM provider via Ollama.

Ollama is optional and disabled by default. When enabled, it gets the same tool
surface as Gemini and must still pass the grounding guard before a reply reaches
the user. This keeps local experimentation cheap without making the product
depend on a local daemon in CI or deployment.
"""

import json
import logging
from collections.abc import Callable

import httpx

from .. import config
from .context import ToolContext

log = logging.getLogger(__name__)


def _ollama_tools(tool_definitions: list[dict]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
            },
        }
        for tool in tool_definitions
    ]


def _arguments(raw: object) -> dict:
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            decoded = json.loads(raw)
            return decoded if isinstance(decoded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def ollama_loop(
    context: ToolContext,
    message: str,
    *,
    system_prompt: str,
    tool_definitions: list[dict],
    clean_args: Callable,
    max_steps: int,
) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": message},
    ]
    tools = _ollama_tools(tool_definitions)

    for _ in range(max_steps):
        with httpx.Client(timeout=config.OLLAMA_TIMEOUT_S) as client:
            response = client.post(
                f"{config.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": config.OLLAMA_MODEL,
                    "messages": messages,
                    "tools": tools,
                    "stream": False,
                    "options": {"temperature": 0.2},
                },
            )
            response.raise_for_status()

        payload = response.json()
        assistant_message = payload.get("message", {})
        tool_calls = assistant_message.get("tool_calls") or []
        if not tool_calls:
            return assistant_message.get("content") or payload.get("response") or ""

        messages.append(assistant_message)
        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name")
            tool = getattr(context, name or "", None)
            try:
                result = (
                    tool(**clean_args(tool, _arguments(fn.get("arguments"))))
                    if tool else {"error": f"unknown tool {name}"}
                )
            except Exception as err:
                log.exception("Ollama tool error: %s", name)
                result = {"error": str(err)}
            messages.append({
                "role": "tool",
                "name": name,
                "content": json.dumps(result, ensure_ascii=False),
            })

    return "Planı kurdum ama açıklamayı kısa kesmek zorunda kaldım; plan kartlarına bakabilirsin."
