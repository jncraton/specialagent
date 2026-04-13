import argparse
from pathlib import Path
from typing import Sequence

from .agent import agent


def _parse_args(args: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="specialagent",
        description="",
    )
    return parser.parse_args(args)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    messages: list[str] = []

    agent()
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
