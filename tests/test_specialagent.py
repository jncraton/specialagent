import sys
from io import StringIO
from specialagent.cli import main


def test_prompt_quit(capsys):
    try:
        main(["--prompt", "/quit"])
    except SystemExit as e:
        exit_code = e.code
    else:
        exit_code = 0

    assert exit_code == 0
