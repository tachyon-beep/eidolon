"""JSON utility functions for extracting structured data from LLM responses"""

import json
import re
from typing import Optional, Dict, Any


def extract_json_from_response(content: str) -> Optional[Dict[str, Any]]:
    """
    Extract JSON object from LLM response text

    Handles:
    - Pure JSON
    - JSON wrapped in markdown code blocks
    - JSON with surrounding text

    Args:
        content: Response text from LLM

    Returns:
        Parsed JSON dict or None if no valid JSON found
    """
    if not content:
        return None

    # Try direct JSON parse first
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in markdown code blocks
    json_block_pattern = r'```(?:json)?\s*(\{.*?\})\s*```'
    matches = re.findall(json_block_pattern, content, re.DOTALL)

    for match in matches:
        try:
            return json.loads(match)
        except json.JSONDecodeError:
            continue

    # Try to find any JSON object in the text
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, content, re.DOTALL)

    for match in matches:
        try:
            parsed = json.loads(match)
            # Only return if it looks like a structured response
            if isinstance(parsed, dict) and len(parsed) > 0:
                return parsed
        except json.JSONDecodeError:
            continue

    return None
