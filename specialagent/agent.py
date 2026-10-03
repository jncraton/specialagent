import json
import os
import sys
import re
import subprocess
import time
from inspect import signature
from pathlib import Path
from contextlib import suppress
from . import tools


def describe_tools():
    """
    Create tool description

    >>> describe_tools()[-1]
    {'name': 'writeFile', 'description': 'Write content to filename', 'parameters': {'type': 'object', 'additionalProperties': False, 'properties': {'filename': {'type': 'string'}, 'content': {'type': 'string'}}, 'required': ['filename', 'content']}}
    """

    return [
        {
            "name": fn.__name__,
            "description": fn.__doc__.strip().splitlines()[0],
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {p: {"type": "string"} for p in signature(fn).parameters},
                "required": list(signature(fn).parameters),
            },
        }
        for fn in map(lambda f: getattr(tools, f), dir(tools))
        if callable(fn)
    ]


def call_model(messages):
    import urllib.request

    payload = {
        "model": os.environ.get("LLM_MODEL", ""),
        "messages": messages,
        "tools": [{"type": "function", "function": tool} for tool in describe_tools()],
        "temperature": 0,
    }

    if effort := os.environ.get("LLM_REASONING_EFFORT", ""):
        payload["reasoning_effort"] = effort

    req = urllib.request.Request(
        os.environ.get("LLM_BASE_URL", "http://localhost:8080/v1/chat/completions"),
        data=json.dumps(payload).encode(),
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
                print(re.sub(r"[{}\'\"]", "", str(res_data.get("usage", {}))))

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

    result = getattr(tools, name)(**args)

    return {"role": "tool", "tool_call_id": str(identifier), "content": result}


def fmt_calls(calls):
    """
    Generate prefetched tool calls

    >>> next(fmt_calls([["exec", "echo hello"]]))["function"]["arguments"]
    '{"command": "echo hello"}'
    """

    for index, call in enumerate(calls):
        yield (
            {
                "id": str(index),
                "type": "function",
                "function": {
                    "name": call[0],
                    "arguments": json.dumps(
                        {
                            k: v
                            for k, v in zip(
                                signature(getattr(tools, call[0])).parameters, call[1:]
                            )
                        }
                    ),
                },
            }
        )


def get_system(system=""):
    with suppress(FileNotFoundError):
        system += Path("~/.agents/AGENTS.md").expanduser().read_text()
        print(f"Loaded {len(system)} byte AGENTS.md")

    if skills := discover_skills():
        print(f"Found {len(skills)} skills")

        system += "\n\ncat matching skills immediately:\n\n"
        system += "\n\n".join(f"{v['desc']}: cat {k}" for k, v in skills.items())

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
    """Main agent loop"""

    prompt = prompt or editor_input(".specialagent.last.prompt.txt")

    cmds = [["exec", f"cat {s}"] for s in get_prompt_skills(prompt, discover_skills())]
    cmds.append(["exec", "(git ls-files || ls) | head -n 30"])
    cmds.extend(
        ["exec", f"cat {f}"]
        for f in set(get_prompt_files(prompt)) | {"makefile", "Makefile"}
        if os.path.isfile(f)
    )

    messages = [
        {"role": "system", "content": system or get_system()},
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": None, "tool_calls": list(fmt_calls(cmds))},
    ]

    while tools := messages[-1].get("tool_calls", []):
        for tool in tools:
            args = json.loads(tool["function"]["arguments"])
            messages.append(run_tool(tool["function"]["name"], args, tool["id"]))

        messages.append(call_model(messages))

    Path(".specialagent.last.session.json").write_text(json.dumps(messages))
    print(messages[-1]["content"])
