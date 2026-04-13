import sys
from io import StringIO
from specialagent.cli import main


def test_quit(tmp_path, capsys, monkeypatch):
  monkeypatch.setattr('sys.stdin', StringIO('/quit\n'))
  try:
    exit_code = main()
  except SystemExit as e:
    exit_code = e.code

  captured = capsys.readouterr()
  assert exit_code == 0
