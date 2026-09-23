import json
import os
import sys
import subprocess
import shlex
import tempfile
import time
from inspect import signature


def editor_input(initial=""):
    """Open $EDITOR with initial text and return the edited text."""

    fd, path = tempfile.mkstemp(suffix=".md", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(initial)

        subprocess.run(
            shlex.split(os.environ.get("EDITOR", "nano")) + [path], check=True
        )

        with open(path, encoding="utf-8") as file:
            return file.read()
    finally:
        os.unlink(path)


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


def call_model(messages, tools):
    import urllib.request

    url = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8080/v1/chat/completions")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "")

    req = urllib.request.Request(
        url,
        data=json.dumps(
            {
                "model": model,
                "messages": messages,
                "tools": [{"type": "function", "function": tool} for tool in tools],
                "temperature": 0.0,
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    print(f"Prompting LLM with {len(req.data)} bytes...")

    for backoff in [0, 1, 2] + [4] * 64:
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode())
                usage = res_data.get("usage", {})

                print(
                    f"LLM generated {usage.get('completion_tokens', 0)} tokens following {usage.get('prompt_tokens', 0)} input tokens"
                )

                return res_data["choices"][0]["message"]
        except urllib.error.HTTPError as e:
            print(f"HTTPError {e.code}: {e.read().decode('utf-8')}")
        time.sleep(backoff)


def run_function(name, args):
    """

    >>> run_function("run_bash", {"command": "echo hello"})
    'hello\\n'
    """

    print(f"Calling {name} with {args}", file=sys.stderr)

    return globals().get(name)(**args)


def build_tool(name):
    """

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

    files = set(f for f in prompt.split() if "." in f and len(f) >= 4)
    files.update(set(f[:-1] for f in files))
    files.update(extra)

    for skill in discover_skills():
        if skill.split("/")[-2] in prompt[:100]:
            files.add(skill)

    files = {f for f in files if os.path.isfile(f)}
    tool_calls = [
        {"name": "run_bash", "arguments": {"command": f"cat {f}"}} for f in files
    ]
    tool_calls.insert(
        0,
        {
            "name": "run_bash",
            "arguments": {"command": "find . -maxdepth 2 -type f | head -n 100"},
        },
    )

    for tool_call_id, tool_call in enumerate(tool_calls):
        result = run_function(tool_call["name"], tool_call["arguments"])

        messages.append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": str(tool_call_id), "type": "function", "function": tool_call}
                ],
            }
        )

        messages.append(
            {
                "role": "tool",
                "tool_call_id": str(tool_call_id),
                "content": result,
            }
        )

    return messages


def agent(prompt="", system=None):
    """
    >>> agent("/quit")
    """

    if not prompt:
        try:
            with open(".specialagent.last.prompt.txt") as f:
                lastprompt = f.read()
        except FileNotFoundError:
            lastprompt = ""

        prompt = editor_input(lastprompt)

    if prompt == "/quit":
        return

    if system == None:
        system = get_system()

    tools = [build_tool(fn) for fn in ("run_bash", "write_file", "replace")]

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    messages.extend(prefetch(prompt, ["makefile", "Makefile"]))

    try:
        with open(".specialagent.last.prompt.txt", "w") as f:
            f.write(prompt)
    except PermissionError:
        print("Unable to write last prompt")

    while True:
        response = call_model(messages, tools)
        messages.append(response)

        tool_calls = response.get("tool_calls", [])

        for tool_call in tool_calls:
            name = tool_call["function"]["name"]
            args = json.loads(tool_call["function"]["arguments"])
            result = run_function(name, args)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result,
                }
            )

        if not tool_calls:
            print(f"LLM assistant message: {response['content']}")
            return


def discover_skills():
    skills = {}

    try:
        for base_dir in [os.path.expanduser("~/.agents/skills")]:
            for skill in os.listdir(base_dir):
                skill_path = os.path.join(base_dir, skill, "SKILL.md")
                content = open(skill_path).read()
                skills[skill_path] = {
                    "desc": content.partition("description:")[-1]
                    .splitlines()[0]
                    .strip(),
                    "content": content,
                }
    except FileNotFoundError:
        pass

    return skills


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
