import json
from typing import Optional, Any, Dict, Set, List
import re

def resolve_genai_schema(input_schema: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Return a copy of the schema with JSON refs flattened for Gemini."""

    if not input_schema:
        return None

    schema_dict = json.loads(json.dumps(input_schema))
    defs = schema_dict.get("$defs", {})
    resolving: Set[str] = set()

    def normalize_any_of(schema_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Gemini requires anyOf to be the only key at its level."""

        any_of = schema_dict.get("anyOf")
        if not isinstance(any_of, list):
            return {"anyOf": any_of}

        meta = {k: v for k, v in schema_dict.items() if k != "anyOf"}
        cleaned_options: List[Any] = []
        for option in any_of:
            cleaned_options.append(option)

        non_null_options = [
            option
            for option in cleaned_options
            if not (isinstance(option, dict) and option.get("type") == "null")
        ]
        has_null = len(non_null_options) != len(cleaned_options)

        if has_null and len(non_null_options) == 1:
            merged = dict(non_null_options[0])
            merged.update({k: v for k, v in meta.items() if k not in ("anyOf",)})
            merged["nullable"] = True
            return merged

        transferable = {
            key: value for key, value in meta.items() if key in {"title", "description"}
        }
        if transferable:
            for option in cleaned_options:
                if isinstance(option, dict):
                    for t_key, t_val in transferable.items():
                        option.setdefault(t_key, t_val)

        return {"anyOf": cleaned_options}

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            ref_value = node.get("$ref")
            base = {}
            if ref_value and ref_value.startswith("#/$defs/"):
                ref_key = ref_value.split("/")[-1]
                if ref_key not in resolving and ref_key in defs:
                    resolving.add(ref_key)
                    base = resolve(defs[ref_key])
                    resolving.remove(ref_key)

            resolved = {}
            for key, value in node.items():
                if key in ("$defs", "$ref"):
                    continue
                resolved[key] = resolve(value)

            if base:
                merged = {}
                merged.update(base)
                merged.update(resolved)
                if "anyOf" in merged:
                    return normalize_any_of(merged)
                return merged
            if "anyOf" in resolved:
                return normalize_any_of(resolved)
            return resolved

        if isinstance(node, list):
            return [resolve(item) for item in node]

        return node
    flattened = resolve(schema_dict)
    if isinstance(flattened, dict):
        flattened.pop("$defs", None)
    return flattened


def parse_json_from_ai(raw_text: str) -> dict:
    """Best-effort JSON extraction for occasionally noisy LLM replies."""
    if not isinstance(raw_text, str):
        raise ValueError("AI response is not text; cannot parse JSON")

    text = raw_text.strip()

    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    start = text.find("{")
    end = text.rfind("}")
    if 0 <= start < end:
        fragment = text[start : end + 1].strip()
        try:
            return json.loads(fragment)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Unable to parse AI JSON response: {exc}") from exc

    raise ValueError("No JSON object found in AI response")