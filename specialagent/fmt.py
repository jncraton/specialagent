import ast
import io
import sys
import tokenize
from pathlib import Path


def format_source(source):
    """Unparse Python source and add a blank line after each DEDENT.

    >>> format_source("def a():\\n    pass\\ndef b():\\n    pass")
    'def a():\\n    pass\\n\\ndef b():\\n    pass\\n'
    """
    code = ast.unparse(ast.parse(source))
    lines = code.splitlines()

    dedent_lines = {
        token.start[0]
        for token in tokenize.generate_tokens(io.StringIO(code).readline)
        if token.type == tokenize.DEDENT
    }

    for line_number in sorted(dedent_lines, reverse=True):
        index = line_number - 1
        if 0 < index < len(lines) and lines[index - 1].strip():
            lines.insert(index, "")

    return "\n".join(lines).rstrip() + "\n"


def remove_comments(source):
    """
    Remove Python comments while preserving comments inside strings.

    >>> remove_comments("x = 1  # note\\ny = '# not a comment'\\n")
    'x = 1  \\ny = \\'# not a comment\\'\\n'
    """
    tokens = tokenize.generate_tokens(io.StringIO(source).readline)

    return tokenize.untokenize(
        tuple(token[:2]) for token in tokens if token.type != tokenize.COMMENT
    )


def reformat_file(path):
    """Read and format a Python file."""
    return remove_comments(Path(path).read_text(encoding="utf-8"))


if __name__ == "__main__":
    print(reformat_file(sys.argv[1]), end="")
