import json
import os
import sys
import re
import subprocess
import time
from inspect import signature
from pathlib import Path
from contextlib import suppress


def exec(command):
    """
    Execute bash command

    >>> exec("echo hello")
    'hello'
    """

    return subprocess.getoutput(command)


def writeFile(filename, content):
    """
    Write content to filename
    """
    Path(filename).write_text(content)


def replace(filename, search, replace):
    """
    Replace text in filename

    >>> import tempfile
    >>> file = tempfile.NamedTemporaryFile(buffering=0)
    >>> file.write(b'hello world')
    11
    >>> replace(file.name, 'world', 'there')
    'replaced 1'

    >>> open(file.name).read()
    'hello there'
    """
    content = Path(filename).read_text()
    count = content.count(search)
    Path(filename).write_text(content.replace(search, replace))

    return f"replaced {count}"


def build_tool(fn):
    """
    Build tool description for initial API call

    >>> build_tool(writeFile)
    {'name': 'writeFile', 'description': 'Write content to filename', 'parameters': {'type': 'object', 'additionalProperties': False, 'properties': {'filename': {'type': 'string'}, 'content': {'type': 'string'}}, 'required': ['filename', 'content']}}
    """

    return {
        "name": fn.__name__,
        "description": fn.__doc__.splitlines()[1].strip(),
        "parameters": {
            "type": "object",
            "additionalProperties": False,
            "properties": {p: {"type": "string"} for p in signature(fn).parameters},
            "required": list(signature(fn).parameters),
        },
    }


def call_model(messages):
    import urllib.request

    tools = [build_tool(fn) for fn in (exec, writeFile, replace)]

    req = urllib.request.Request(
        os.environ.get("LLM_BASE_URL", "http://localhost:8080/v1/chat/completions"),
        data=json.dumps(
            {
                "model": os.environ.get("LLM_MODEL", ""),
                "messages": messages,
                "tools": [{"type": "function", "function": tool} for tool in tools],
                "temperature": 0,
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('LLM_API_KEY', '')}",
        },
        method="POST",
    )

    print(f"Prompt LLM with {len(req.data)} bytes...")

    for delay in range(20):
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.load(response)
                usage = res_data.get("usage", {})

                print(f"- Read {usage.get('prompt_tokens', 0)} input tokens")
                print(f"- Generated {usage.get('completion_tokens', 0)} tokens")

                return res_data["choices"][0]["message"]
        except urllib.error.HTTPError as e:
            print(f"HTTPError {e.code}: {e.read().decode()}")
        time.sleep(delay)


def run_tool(name, args, identifier):
    """
    Run tool with args producing formatted response object

    >>> run_tool("exec", {"command": "echo hello"}, "1")
    {'role': 'tool', 'tool_call_id': '1', 'content': 'hello'}
    """

    print(f"Calling {name} with {args}", file=sys.stderr)

    result = globals().get(name)(**args)

    return {"role": "tool", "tool_call_id": str(identifier), "content": result}


def prefetch_sh(cmd):
    """
    Return a pair of messages synthesizing a completed tool call

    >>> prefetch_sh("echo hello")[1]["content"]
    'hello'
    """
    prefetch_sh.idx += 1
    return [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": str(prefetch_sh.idx),
                    "type": "function",
                    "function": {
                        "name": "exec",
                        "arguments": json.dumps({"command": cmd}),
                    },
                },
            ],
        },
        run_tool("exec", {"command": cmd}, prefetch_sh.idx),
    ]


prefetch_sh.idx = 0


def get_system(system=""):
    with suppress(FileNotFoundError):
        system += open(os.path.expanduser("~/.agents/AGENTS.md")).read()
        print(f"Loaded {len(system)} byte AGENTS.md")

    if skills := discover_skills():
        print(f"Found {len(skills)} skills")

        system += (
            "\n\n## Skills\n\ncat matching skills before starting tasks:\n\n"
            + "\n\n".join(f"{v['desc']}: cat {k}" for k, v in skills.items())
        )

    return system


def discover_skills():
    return {
        f"{Path('~') / Path(path).relative_to(Path.home())}": {
            "desc": content.partition("description:")[2].splitlines()[0].strip(),
            "content": content,
        }
        for path in Path("~/.agents/skills").expanduser().glob("*/SKILL.md")
        if (content := path.read_text())
    }


def get_prompt_files(prompt):
    """
    Get everything that looks like a file from a prompt

    >>> get_prompt_files("Read readme.md. Check test/test.c, delete.")
    ['readme.md', 'test/test.c']
    """

    return re.findall(r"\b[\w/-]+\.[\w./-]+\b", prompt)


def get_prompt_skills(prompt, skills):
    """
    Get skill directly mentioned by name in a prompt

    >>> get_prompt_skills("Use search and gen-deck", {"s/search/SKILL.md": "", "s/bad/SKILL.md": "", "s/gen-deck/SKILL.md": ""})
    ['s/search/SKILL.md', 's/gen-deck/SKILL.md']
    """

    return [s for s in skills if s.split("/")[-2] in prompt[:100]]


def editor_input(path):
    """Open $EDITOR with initial text and return the edited text."""

    subprocess.run([os.environ.get("EDITOR", "nano"), path], check=True)
    return Path(path).read_text()


def agent(prompt="", system=None):
    """
    Main agent loop

    >>> agent("/quit")
    """

    if prompt == "/quit":
        return

    prompt = prompt or editor_input(".specialagent.last.prompt.txt")

    messages = [
        {"role": "system", "content": system or get_system()},
        {"role": "user", "content": prompt},
    ]

    for skill in get_prompt_skills(prompt, discover_skills()):
        messages += prefetch_sh(f"cat {skill}")

    messages += prefetch_sh("(git ls-files || ls) | head -n 30")

    for f in set(get_prompt_files(prompt)) | {"makefile", "Makefile"}:
        if os.path.isfile(f):
            messages += prefetch_sh(f"cat {f}")

    messages.append(call_model(messages))

    while tools := messages[-1].get("tool_calls", []):
        for tool in tools:
            args = json.loads(tool["function"]["arguments"])
            messages.append(run_tool(tool["function"]["name"], args, tool["id"]))

        messages.append(call_model(messages))

    Path(".specialagent.last.session.json").write_text(json.dumps(messages))
    print(messages[-1]["content"])


if __name__ == "__main__":
    agent()
