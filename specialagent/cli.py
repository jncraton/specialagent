import argparse
from pathlib import Path
from typing import Sequence

from .agent import agent


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="specialagent",
        description="",
    )
    parser.add_argument("-p", "--prompt", type=str, help="set the prompt from a string")
    args = parser.parse_args(argv)

    agent(args.prompt or "")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
