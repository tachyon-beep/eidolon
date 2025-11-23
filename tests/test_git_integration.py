import subprocess

from eidolon.git_integration import GitManager
import pytest


def test_is_git_repo_false(monkeypatch, tmp_path):
    gm = GitManager(tmp_path)

    def fake_run(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert gm.is_git_repo() is False


def test_get_changed_files_not_repo(tmp_path):
    gm = GitManager(tmp_path)
    with pytest.raises(ValueError):
        gm.get_changed_files()


def test_get_changed_files_parsing(monkeypatch, tmp_path):
    gm = GitManager(tmp_path)

    def fake_run(args, cwd=None, capture_output=True, text=True, timeout=5):
        class Result:
            def __init__(self, returncode, stdout="", stderr=""):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = stderr
        cmd = args[1] if isinstance(args, list) else args
        if args[:2] == ["git", "rev-parse"]:
            return Result(0, stdout="true\n")
        if args[:2] == ["git", "diff"]:
            return Result(0, stdout="M\ta.py\nA\tb.py\nD\tc.py\nR100\td.py\te.py\n")
        if args[:3] == ["git", "ls-files", "--others"]:
            return Result(0, stdout="f.py\n")
        return Result(0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    changes = gm.get_changed_files(base="HEAD", file_extensions={".py"})
    assert changes.modified == ["a.py", "e.py"]
    assert changes.added == ["b.py", "f.py"]
    assert changes.deleted == ["c.py"]
    assert changes.renamed == {"d.py": "e.py"}
    assert set(changes.all_changed) == {"a.py", "e.py", "b.py", "f.py"}
