"""Tool definitions, parsing, and execution for HiggsAudioM3 v3.5 tool use."""

import json
import re

MAX_TOOL_CALLS_PER_TURN = 3

CALCULATOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a math expression. Supports +, -, *, /, **, parentheses.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate, e.g. '2 + 3 * 4'",
                    }
                },
                "required": ["expression"],
            },
        },
    }
]

_SAFE_MATH_RE = re.compile(r"^[0-9+\-*/()._ ]+$")


def safe_eval_math(expression: str) -> float:
    """Evaluate a math expression using only safe characters."""
    expr = expression.strip()
    if not _SAFE_MATH_RE.match(expr):
        raise ValueError(f"Unsafe expression: {expr!r}")
    return float(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307


def execute_tool_call(name: str, args: dict) -> dict:
    """Execute a tool call and return the result."""
    if name == "calculate":
        expression = args.get("expression", "")
        result = safe_eval_math(expression)
        return {"name": name, "result": result}
    return {"name": name, "error": f"Unknown tool: {name}"}


_TOOL_CALL_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)


def _normalize_tool_call(raw: dict) -> dict:
    """Normalize a tool call dict into {name, arguments} regardless of format."""
    if "function" in raw:
        func = raw["function"]
        name = func.get("name", "unknown")
        args_raw = func.get("arguments", func.get("parameters", "{}"))
    else:
        name = raw.get("name", "unknown")
        args_raw = raw.get("arguments", raw.get("parameters", "{}"))

    if isinstance(args_raw, str):
        args_raw = json.loads(args_raw)
    return {"name": name, "arguments": args_raw}


def parse_tool_calls(text: str) -> list[dict]:
    """Extract tool call dicts from <tool_call> tags. Returns list of {name, arguments}."""
    results = []
    for match in _TOOL_CALL_RE.finditer(text):
        try:
            parsed = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            continue
        items = parsed if isinstance(parsed, list) else [parsed]
        for item in items:
            results.append(_normalize_tool_call(item))
    return results


def build_system_prompt(base_prompt: str, tools_enabled: bool) -> str:
    """Build system prompt, optionally embedding tool definitions."""
    if not tools_enabled:
        return base_prompt
    tools_json = json.dumps({"tools": CALCULATOR_TOOLS})
    return f"{base_prompt}\n<tools>\n{tools_json}\n</tools>"
