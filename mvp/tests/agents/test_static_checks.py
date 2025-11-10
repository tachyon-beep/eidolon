"""Tests for static analysis checks."""

from eidolon_mvp.agents.static_checks import StaticAnalyzer, analyze_function_code


def test_complexity_check():
    """Test complexity detection."""
    code = """
def complex_function(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        if x > 50:
                            return True
    return False
"""

    findings = analyze_function_code("complex_function", code, "test.py")

    # Should find high complexity
    complexity_findings = [f for f in findings if f.type == "performance"]
    assert len(complexity_findings) > 0
    assert "complexity" in complexity_findings[0].description.lower()


def test_unclosed_resources():
    """Test detection of unclosed file handles."""
    code = """
def bad_file_handler():
    f = open("test.txt")
    data = f.read()
    return data
"""

    findings = analyze_function_code("bad_file_handler", code, "test.py")

    # Should find unclosed file
    file_findings = [f for f in findings if "context manager" in f.description.lower()]
    assert len(file_findings) > 0
    assert file_findings[0].severity == "high"


def test_null_safety():
    """Test detection of potential None access."""
    code = """
def risky_function(data):
    user = data.get("user")
    return user.name  # Might be None!
"""

    findings = analyze_function_code("risky_function", code, "test.py")

    # Should find potential None access
    none_findings = [f for f in findings if "None" in f.description]
    assert len(none_findings) > 0


def test_bare_except():
    """Test detection of bare except clauses."""
    code = """
def bad_exception_handler():
    try:
        dangerous_operation()
    except:
        pass
"""

    findings = analyze_function_code("bad_exception_handler", code, "test.py")

    # Should find bare except
    except_findings = [f for f in findings if "except" in f.description.lower()]
    assert len(except_findings) > 0


def test_clean_function():
    """Test that clean code produces no findings."""
    code = """
def clean_function(x: int) -> int:
    '''Simple function with no issues.'''
    if x > 0:
        return x * 2
    return 0
"""

    findings = analyze_function_code("clean_function", code, "test.py")

    # Should find minimal or no issues
    critical_findings = [f for f in findings if f.severity in ["critical", "high"]]
    assert len(critical_findings) == 0


def test_with_statement_ok():
    """Test that proper context manager usage is recognized."""
    code = """
def good_file_handler():
    with open("test.txt") as f:
        data = f.read()
    return data
"""

    findings = analyze_function_code("good_file_handler", code, "test.py")

    # Should NOT flag this as unclosed
    file_findings = [f for f in findings if "context manager" in f.description.lower()]
    assert len(file_findings) == 0
