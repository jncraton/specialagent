import json
import os
import subprocess
from inspect import signature


SKILLS = {}


def exec(command):
    """
    Executes a bash command and returns the output.

    >>> exec('echo "hello"')
    'hello\\n'
    """

    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return f"{result.stdout}{result.stderr}"


def write(path, content):
    """
    Writes content to a file at the specified path.

    >>> import tempfile, os
    >>> with tempfile.NamedTemporaryFile(delete=False) as tmp:
    ...     write(tmp.name, 'test')
    ...     path = tmp.name
    'File written to ...
    >>> with open(path, 'r') as f:
    ...     f.read()
    ...     os.remove(path)
    'test'
    """
    with open(path, "w") as f:
        f.write(content)
    return f"File written to {path}"


def replace(path, search, replace):
    """
    Replaces text in file

    >>> import tempfile, os
    >>> with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp:
    ...     _ = tmp.write('hello world')
    ...     path = tmp.name
    >>> replace(path, 'world', 'there')
    'Replaced 1 in ...
    >>> with open(path, 'r') as f:
    ...     f.read()
    ...     os.remove(path)
    'hello there'
    """
    with open(path, "r") as f:
        content = f.read()

    count = content.count(search)

    with open(path, "w") as f:
        f.write(content.replace(search, replace))

    return f"Replaced {count} in {path}"


def load_skill(description):
    """
    Loads a skill by name
    """


def exit():
    """
    Exit session
    """

    pass


def call_model(messages, tools):
    import urllib.request

    url = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8080/v1/chat/completions")
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "gemma-4-31b-it")

    req = urllib.request.Request(
        url,
        data=json.dumps(
            {
                "model": model,
                "messages": messages,
                "tools": [{"type": "function", "function": tool} for tool in tools],
                "tool_choice": "required",
                "temperature": 0.3,
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    print(f"Prompting {model} with {len(req.data)} bytes...")

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode())
            usage = res_data.get("usage", {})

            print(
                f"Prompt: {usage.get('prompt_tokens', 0)} | "
                f"Response: {usage.get('completion_tokens', 0)} | "
                f"Total: {usage.get('total_tokens', 0)}"
            )

            return res_data["choices"][0]["message"]
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code}: {e.read().decode('utf-8')}")
        exit(1)


def run_function(name, args):
    """

    >>> run_function("exec", {"command": "echo hello"})
    Calling exec with {'command': 'echo hello'}
    'hello\\n'
    """

    print(f"Calling {name} with {args}")

    return globals().get(name)(**args)


def build_tool(name):
    """

    >>> build_tool("exec")
    {'name': 'exec', 'description': 'Executes', 'parameters': {'type': 'object', 'properties': {'command': {'type': 'string'}}, 'required': ['command']}}

    >>> build_tool("write")
    {'name': 'write', 'description': 'Writes', 'parameters': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'content': {'type': 'string'}}, 'required': ['path', 'content']}}
    """

    params = list(signature(globals()[name]).parameters.keys())

    return {
        "name": name,
        "description": globals()[name].__doc__.split()[0],
        "parameters": {
            "type": "object",
            "properties": {p: {"type": "string"} for p in params},
            "required": params,
        },
    }


def agent(prompt, system=""):
    """
    >>> agent("/quit")
    """

    if prompt == "/quit":
        return

    tools = [build_tool(fn) for fn in ("exec", "write", "replace", "exit")]

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

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

            if name == "exit":
                return

        if not tool_calls:
            print(response)


def discover_skills():
    for base_dir in [os.path.expanduser("~/.agents/skills")]:
        for skill in os.listdir(base_dir):
            content = open(os.path.join(base_dir, skill, "SKILL.md")).read()
            SKILLS[skill] = {
                "desc": content.partition("description:")[-1].splitlines()[0].strip(),
                "content": content,
            }

    print(f"Discovered {len(SKILLS)} skills")

    return len(SKILLS)


if __name__ == "__main__":
    system = ""

    try:
        system = open(os.path.expanduser("~/.agents/AGENTS.md")).read()
        print(f"Loaded {len(system)} byte AGENTS.md")
    except FileNotFoundError:
        pass

    if discover_skills():
        system += "\n\n## Available Skills\n\n" + "\n".join(
            f"- {k}: {v['desc']}" for k, v in SKILLS.items()
        )

    agent(input("Task: "), system)
