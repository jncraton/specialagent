import json
import os
import subprocess
from inspect import signature


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


def call_gemini(messages, tools):
    import urllib.request

    url = "https://generativelanguage.googleapis.com/v1beta/models/gemma-4-26b-a4b-it:generateContent"
    api_key = os.environ.get("GEMINI_API_KEY")
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}
    data = json.dumps(
        {"contents": messages, "tools": [{"function_declarations": tools}]}
    ).encode()

    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode())


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

    tools = [build_tool(fn) for fn in ("run_bash", "write_file")]

    messages = []
    messages.append({"role": "user", "parts": [{"text": prompt}]})

    while True:
        response = call_gemini(messages, tools)
        parts = response["candidates"][0]["content"]["parts"]
        text_parts = [p for p in parts if "text" in p]
        function_calls = [p for p in parts if "functionCall" in p]

        messages.append(response["candidates"][0]["content"])

        if len(function_calls) == 0:
            for text_part in text_parts:
                print(text_part["text"])
            print("Task complete.")
            break

        for call in function_calls:
            result = run_function(
                call["functionCall"]["name"], call["functionCall"]["args"]
            )

            messages.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": call["functionCall"]["name"],
                                "response": {"content": result},
                            }
                        }
                    ],
                }
            )


if __name__ == "__main__":
    agent(input("Task: "))
