from eidolon.utils.json_utils import extract_json_from_response


def test_extract_json_plain():
    content = '{"a": 1, "b": 2}'
    parsed = extract_json_from_response(content)
    assert parsed == {"a": 1, "b": 2}


def test_extract_json_code_block():
    content = "Here is data:\n```json\n{\"foo\": \"bar\"}\n```"
    parsed = extract_json_from_response(content)
    assert parsed == {"foo": "bar"}


def test_extract_json_embedded_text():
    content = "start {\"x\":3,\"y\":4} end"
    parsed = extract_json_from_response(content)
    assert parsed == {"x": 3, "y": 4}


def test_extract_json_invalid_returns_none():
    assert extract_json_from_response("no json here") is None
