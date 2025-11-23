from pathlib import Path

from eidolon.code_writer import CodeWriter


def test_write_and_rollback(tmp_path):
    writer = CodeWriter(project_path=tmp_path)

    # create new file
    res = writer.write_file("a.py", "print('hi')\n", create_backup=False)
    assert res["operation"] == "create"
    assert (tmp_path / "a.py").exists()

    # modify with backup
    res2 = writer.write_file("a.py", "print('bye')\n", create_backup=True)
    assert res2["operation"] == "modify"
    assert (tmp_path / "a.py").read_text() == "print('bye')\n"
    assert res2["backup"] is not None

    rollback = writer.rollback()
    # Both modify (restore) and create (delete) are rolled back
    assert rollback["rollback_count"] == 2
    assert not (tmp_path / "a.py").exists()

    writer.commit_session()
    assert writer.get_changes() == []
