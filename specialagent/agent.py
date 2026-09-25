import json
import os
import glob
import sys
import re
import subprocess
import time
from inspect import signature


def editor_input(path):
    """Open $EDITOR with initial text and return the edited text."""

    subprocess.run([os.environ.get("EDITOR", "nano"), path], check=True)

    with open(path, encoding="utf-8") as file:
        return file.read()


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

    >>> import tempfile
    >>> file = tempfile.NamedTemporaryFile()
    >>> write_file(file.name, 'test')
    'Wrote to ...

    >>> open(file.name, 'r').read()
    'test'
    """
    with open(filename, "w") as f:
        f.write(content)
    return f"Wrote to {filename}"


def replace(path, search, replace):
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
    with open(path, "r") as f:
        content = f.read()

    count = content.count(search)

    with open(path, "w") as f:
        f.write(content.replace(search, replace))

    return f"Replaced {count} in {path}"


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


def build_tool(name):
    """
    Build tool description for initial API call

    >>> build_tool("run_bash")
    {'name': 'run_bash', 'description': 'Executes bash command and returns output', 'parameters': {'type': 'object', 'properties': {'command': {'type': 'string'}}, 'required': ['command']}}

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


def synthesize_tool_call(name, arguments):
    """
    Return a pair of messages synthesizing a completed tool call

    >>> synthesize_tool_call("run_bash", {"command": "echo hello"})[1]["content"]
    'hello\\n'
    """
    synthesize_tool_call.idx += 1
    return [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": str(synthesize_tool_call.idx),
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }
            ],
        },
        run_tool(name, arguments, synthesize_tool_call.idx),
    ]


synthesize_tool_call.idx = 0


def get_prompt_files(prompt):
    """
    Heuristic to grab everything that looks like a file from a prompt

    >>> get_prompt_files("Read readme.md. Check test.c, delete.")
    ['readme.md', 'test.c']
    """

    return re.findall(r"\b[\w-]+\.[\w.-]+\b", prompt)


def prefetch(prompt, extra=set()):
    """Create synthetic tool call and result messages

    >>> prefetch("Check readme.md")[0]['role']
    'assistant'

    >>> prefetch("Check readme.md")[1]['role']
    'tool'

    >>> len(prefetch("hi", ['makefile'])) > len(prefetch("hi"))
    True
    """

    messages = []

    for skill in discover_skills():
        if skill.split("/")[-2] in prompt[:100]:
            messages += synthesize_tool_call("run_bash", {"command": f"cat {skill}"})

    messages += synthesize_tool_call(
        "run_bash",
        {"command": "find . -maxdepth 2 -type f -printf '%P\n' | head -n 100"},
    )

    for f in set(get_prompt_files(prompt)) | set(extra):
        if os.path.isfile(f):
            messages += synthesize_tool_call("run_bash", {"command": f"cat {f}"})

    return messages


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

    messages.extend(prefetch(prompt, ["makefile", "Makefile"]))

    while True:
        response = call_model(messages)
        messages.append(response)

        tool_calls = response.get("tool_calls", [])

        for tool_call in tool_calls:
            name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])
            messages.append(run_tool(name, args, tool_call["id"]))

        with open(".specialagent.last.session.json", "w") as f:
            f.write(json.dumps(messages))

        if not tool_calls:
            print(f"LLM assistant message: {response['content']}")
            return


def discover_skills():
    return {
        path: {
            "desc": content.partition("description:")[2].splitlines()[0].strip(),
            "content": content,
        }
        for path in glob.glob(os.path.expanduser("~/.agents/skills/*/SKILL.md"))
        if (content := open(path).read())
    }


def get_system():
    try:
        system = open(os.path.expanduser("~/.agents/AGENTS.md")).read()
        print(f"Loaded {len(system)} byte AGENTS.md")
    except FileNotFoundError:
        system = ""

    if skills := discover_skills():
        print(f"Discovered {len(skills)} skills")

        system += (
            "\n\n## Skills\n\nRead matching skills using cat before starting tasks:\n\n"
            + "\n".join(f"- `cat {k}`: {v['desc']}" for k, v in skills.items())
        )

    return system


if __name__ == "__main__":
    agent()
