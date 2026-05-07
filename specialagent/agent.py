import json
import os
import subprocess
from inspect import signature


system = """
Never comment code or make unnecessary changes. Favor pure functions. Only commit changes if requested. Avoid dependencies.

### JS

Prefer single quotes and avoid semicolons.

### Python.

Follow black. Favor doctest for testing and use docstrings only for doctests.

### SQL

Use lowercase modern style.

### C-like

Use one true brace with two space indentation.

### Web

Favor brutalism via classless, semantic markup and simple styles to maintaining responsiveness and accessibility. Favor inline scripts and styles with no external dependencies. Prefer globally available id variables rather than selectors.

Only make tool calls. Assistant messages are discarded.
""".strip()


def run_bash(command):
    """
    Executes a bash command and returns the output.

    >>> run_bash('echo "hello"')
    'hello\\n'
    """

    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return f"{result.stdout}{result.stderr}"


def write_file(path, content):
    """
    Writes content to a file at the specified path.

    >>> import tempfile
    >>> with tempfile.NamedTemporaryFile() as tmp:
    ...     write_file(tmp.name, 'test')
    'File written to ...
    """
    with open(path, "w") as f:
        f.write(content)
    return f"File written to {path}"


def success():
    """
    Reports success to the user
    """

    pass


def call_model(messages, tools):
    import urllib.request

    url = "http://127.0.0.1:8080/v1/chat/completions"
    api_key = ""
    model = ""

    if os.environ.get("GEMINI_API_KEY"):
        url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        api_key = os.environ.get("GEMINI_API_KEY")
        model = "gemma-4-31b-it"

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

    >>> run_function("run_bash", {"command": "echo hello"})
    Executing run_bash with {'command': 'echo hello'}
    'hello\\n'
    """

    print(f"Executing {name} with {args}")

    return globals().get(name)(**args)


def build_tool(name):
    """

    >>> build_tool("run_bash")
    {'name': 'run_bash', 'description': 'Executes', 'parameters': {'type': 'object', 'properties': {'command': {'type': 'string'}}, 'required': ['command']}}

    >>> build_tool("write_file")
    {'name': 'write_file', 'description': 'Writes', 'parameters': {'type': 'object', 'properties': {'path': {'type': 'string'}, 'content': {'type': 'string'}}, 'required': ['path', 'content']}}
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


def agent(prompt):
    """
    >>> agent("/quit")
    """

    if prompt == "/quit":
        return

    tools = [build_tool(fn) for fn in ("run_bash", "write_file", "success")]

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

            if name == "success":
                return
        else:
            break


if __name__ == "__main__":
    agent(input("Task: "))
