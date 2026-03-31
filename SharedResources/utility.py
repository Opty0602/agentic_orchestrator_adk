"Utiliy tools for extracting dicts from LLM output and converting dicts to TOON format for saving tokens"

import json
import re

def _try_parse_strict_json(s: str):
    try:
        return json.loads(s)
    except Exception as e:
        return None

def _try_parse_loose_json(s: str):
    """
    Last-resort attempt:
    - Fix single quotes to double quotes
    - Remove trailing commas
    - Remove illegal characters outside JSON
    """

    cleaned = s

    # replace single quotes with double quotes
    cleaned = re.sub(r"'", '"', cleaned)

    # remove trailing commas before } or ]
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)

    # attempt parse
    try:
        return json.loads(cleaned)
    except Exception as e:
        return None


def parse_llm_json_output(llm_output_str: str):
    """
    Attempts to extract JSON from an LLM output.
    Strategy:
      1. Look for code blocks ```json ... ```
      2. Look for any {...} block
      3. Attempt a 'loose' JSON fix (replace single quotes, trailing commas)
      4. If everything fails, return original string
    """

    if not isinstance(llm_output_str, str):
        return llm_output_str

    text = llm_output_str.strip()

    # 1. Extract from ```json code blocks
    code_block_match = re.search(r"```json(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if code_block_match:
        candidtae = code_block_match.group(1).strip()
        parsed = _try_parse_strict_json(candidate)
        if parsed is not None:
            return parsed

    # 2. Extract first {...} OR [...] block
    brace_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
    if brace_match:
        candidate = brace_match.group(0)
        parsed = _try_parse_strict_json(candidate)
        if parsed is not None:
            return parsed
        # Try salvage
        parsed = _try_parse_loose_json(candidate)
        if parsed is not None:
            return parsed
    # 3. Loose salvage of entire string
    parsed = _try_parse_loose_json(text)
    if parsed is not None:
        return parsed
    # 4. Give up but return original string
    return llm_output_str

def convert_to_toon(data, max_inline_list_items=5):
    """
    Converts a Python dictionary or a JSON string into a custom TOON format.

    Args:
        data: The dict, or JSON string to convert.
        max_inline_list_items: The maximum number of simple list items to display
                               on a single line before breaking them into multiple lines.

    Returns:
        A string representing the data in TOON format.
    """
    if isinstance(data, str):
        # Use the robust parser to handle potentially malformed JSON strings
        parsed_data = parse_llm_json_output(data)
        if isinstance(parsed_data, str): # Parsing failed
            return parsed_data
        data = parsed_data

    if not isinstance(data, (dict, list)):
        return str(data)

    def _format_value(value):
        """Safely format values, handling None and escaping strings."""
        if value is None:
            return "null"
        if isinstance(value, str):
            # If a string contains commas or newlines, quote it to avoid parsing issues.
            if ',' in value or '\n' in value:
                return f'"{value}"'
        return str(value)

    def _is_simple_list(lst):
        """Check if a list contains only non-dict/list items."""
        return all(not isinstance(item, (dict, list)) for item in lst)

    def _is_uniform_list_of_dicts(lst):
        """Check if a list contains only dictionaries."""
        if not lst or not isinstance(lst[0], dict):
            return False
        first_keys = set(lst[0].keys())
        return all(isinstance(item, dict) and set(item.keys()) == first_keys for item in lst)

    def _build_toon(item, indent_level=0):
        indent = "  " * indent_level
        lines = []

        if isinstance(item, dict):
            for key, value in item.items():
                if isinstance(value, dict):
                    lines.append(f"{indent}{key}:")
                    lines.append(_build_toon(value, indent_level + 1))
                elif isinstance(value, list):
                    if not value:
                        lines.append(f"{indent}{key}[0]: []")
                    elif _is_uniform_list_of_dicts(value):
                        # Special compact format for uniform list of dicts
                        keys = value[0].keys()
                        header = ",".join(keys)
                        lines.append(f"{indent}{key}[{len(value)}]{{{header}}}:")
                        for sub_item in value:
                            # Ensure values are in the same order as keys
                            row_values = [_format_value(sub_item.get(k)) for k in keys]
                            lines.append(f"{indent}  {','.join(row_values)}")
                    elif _is_simple_list(value):
                        list_str = ",".join(map(_format_value, value))
                        if len(value) > max_inline_list_items:
                             lines.append(f"{indent}{key}[{len(value)}]:")
                             for v in value:
                                 lines.append(f"{indent}  - {_format_value(v)}")
                        else:
                            lines.append(f"{indent}{key}[{len(value)}]: {list_str}")
                    else: # Mixed or non-uniform list of dicts
                        lines.append(f"{indent}{key}[{len(value)}]:")
                        for sub_item in value:
                            # Render each item as a block
                            lines.append(f"{indent}  -")
                            lines.append(_build_toon(sub_item, indent_level + 2))
                else:
                    lines.append(f"{indent}{key}: {_format_value(value)}")
        elif isinstance(item, list):
             # This case is for when the root item is a list
             return "\n".join(_build_toon(i, indent_level) for i in item)

        return "\n".join(lines)

    return _build_toon(data)
    