import json
import os
import glob
import sys
import re
import subprocess
import time
from inspect import signature
from pathlib import Path
from contextlib import suppress


def run_bash(command):
    """
    Executes bash command and returns output

    >>> run_bash('echo "hello"')
    'hello\\n'
    """

    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return f"{result.stdout}{result.stderr}"


def write_file(filename, content):
    """
    Writes content to file specified by filename
    """
    Path(filename).write_text(content)
    return f"Wrote to {filename}"


def replace(filename, search, replace):
    """
    Replaces text in file

    >>> import tempfile
    >>> file = tempfile.NamedTemporaryFile(buffering=0)
    >>> file.write(b'hello world')
    11
    >>> replace(file.name, 'world', 'there')
    'Replaced 1 in ...

    >>> open(file.name).read()
    'hello there'
    """
    content = Path(filename).read_text()
    count = content.count(search)
    Path(filename).write_text(content.replace(search, replace))

    return f"Replaced {count} in {filename}"


def build_tool(name):
    """
    Build tool description for initial API call

    >>> build_tool("write_file")
    {'name': 'write_file', 'description': 'Writes content to file specified by filename', 'parameters': {'type': 'object', 'properties': {'filename': {'type': 'string'}, 'content': {'type': 'string'}}, 'required': ['filename', 'content']}}
    """

    params = list(signature(globals()[name]).parameters.keys())

    return {
        "name": name,
        "description": globals()[name].__doc__.splitlines()[1].strip(),
        "parameters": {
            "type": "object",
            "properties": {p: {"type": "string"} for p in params},
            "required": params,
        },
    }


def call_model(messages, tools=None):
    import urllib.request

    tools = tools or [build_tool(fn) for fn in ("run_bash", "write_file", "replace")]

    req = urllib.request.Request(
        os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8080/v1/chat/completions"),
        data=json.dumps(
            {
                "model": os.environ.get("LLM_MODEL", ""),
                "messages": messages,
                "tools": [{"type": "function", "function": tool} for tool in tools],
                "temperature": 0.0,
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('LLM_API_KEY', '')}",
        },
        method="POST",
    )

    print(f"\nPrompting LLM with {len(req.data)} bytes...")

    for backoff in [0, 1, 2] + [4] * 64:
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode())
                usage = res_data.get("usage", {})

                print(f"- Read {usage.get('prompt_tokens', 0)} input tokens")
                print(f"- Generated {usage.get('completion_tokens', 0)} tokens")

                return res_data["choices"][0]["message"]
        except urllib.error.HTTPError as e:
            print(f"HTTPError {e.code}: {e.read().decode('utf-8')}")
        time.sleep(backoff)


def run_tool(name, args, tool_call_id):
    """
    Run tool with args producing formatted response object

    >>> run_tool("run_bash", {"command": "echo hello"}, "1")
    {'role': 'tool', 'tool_call_id': '1', 'content': 'hello\\n'}
    """

    print(f"Calling {name} with {args}", file=sys.stderr)

    result = globals().get(name)(**args)

    return {
        "role": "tool",
        "tool_call_id": str(tool_call_id),
        "content": result,
    }


def prefetch_sh(cmd):
    """
    Return a pair of messages synthesizing a completed tool call

    >>> prefetch_sh("echo hello")[1]["content"]
    'hello\\n'
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
                        "name": "run_bash",
                        "arguments": json.dumps({"command": cmd}),
                    },
                },
            ],
        },
        run_tool("run_bash", {"command": cmd}, prefetch_sh.idx),
    ]


prefetch_sh.idx = 0


def get_system(system=""):
    with suppress(FileNotFoundError):
        system += open(os.path.expanduser("~/.agents/AGENTS.md")).read()
        print(f"Loaded {len(system)} byte AGENTS.md")

    if skills := discover_skills():
        print(f"Discovered {len(skills)} skills")

        system += (
            "\n\n## Skills\n\ncat matching skills before starting tasks:\n\n"
            + "\n".join(f"- `cat {k}`: {v['desc']}" for k, v in skills.items())
        )

    return system


def discover_skills():
    return {
        path: {
            "desc": content.partition("description:")[2].splitlines()[0].strip(),
            "content": content,
        }
        for path in glob.glob(os.path.expanduser("~/.agents/skills/*/SKILL.md"))
        if (content := open(path).read())
    }


def get_prompt_files(prompt):
    """
    Heuristic to grab everything that looks like a file from a prompt

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

    while True:
        messages.append(call_model(messages))

        tool_calls = messages[-1].get("tool_calls", [])

        for tool_call in tool_calls:
            name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])
            messages.append(run_tool(name, args, tool_call["id"]))

        Path(".specialagent.last.session.json").write_text(json.dumps(messages))

        if not tool_calls:
            print(f"LLM assistant message: {messages[-1]['content']}")
            return


if __name__ == "__main__":
    agent()
