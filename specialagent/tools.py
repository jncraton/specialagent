import subprocess
import pathlib


def exec(command):
    """
    Execute bash command

    >>> exec("echo hello")
    'hello'
    """

    return subprocess.getoutput(command)


def writeFile(filename, content):
    """Write content to filename"""
    pathlib.Path(filename).write_text(content)


def editFile(filename, old, new):
    """
    Replace old with new substring in filename

    >>> editFile('makefile','cucumber','lint')
    '0 replaced'
    >>> editFile('makefile','lint','cucumber')
    '1 replaced'
    >>> editFile('makefile','cucumber','lint')
    '1 replaced'
    """
    content = pathlib.Path(filename).read_text()
    pathlib.Path(filename).write_text(content.replace(old, new))

    return f"{content.count(old)} replaced"
