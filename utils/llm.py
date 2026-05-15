"""
llm.py — Thin wrapper around the Anthropic SDK used by all agents.

All agents call `llm_call(system, user)` and get back a plain string.
JSON parsing is handled by each agent individually.
"""
import json
import anthropic
import config


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not config.ANTHROPIC_API_KEY:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or export it as an environment variable."
            )
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def llm_call(system: str, user: str, max_tokens: int | None = None) -> str:
    """
    Send a single system+user message to the configured LLM and return
    the text of the first content block.
    """
    client = _get_client()
    response = client.messages.create(
        model=config.LLM_MODEL,
        max_tokens=max_tokens or config.LLM_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return response.content[0].text.strip()


def llm_json(system: str, user: str, max_tokens: int | None = None) -> dict | list:
    """
    Like llm_call but strips markdown fences and parses JSON.
    Raises ValueError if the response is not valid JSON.
    """
    raw = llm_call(system, user, max_tokens)
    # Strip ```json ... ``` fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned non-JSON response: {e}\n\nRaw response:\n{raw[:500]}")
