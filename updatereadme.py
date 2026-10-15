import inspect
import importlib.util
import sys
import os
import re


def get_tools():
    """
    Extract tool names and docstrings from specialagent/tools.py
    """
    tools = []
    module_name = "specialagent.tools"

    current_dir = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.join(current_dir, "specialagent", "tools.py")

    if not os.path.exists(module_path):
        module_path = os.path.join(current_dir, "tools.py")

    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj) and not name.startswith("_"):
            doc = inspect.getdoc(obj) or ""
            tools.append((name, doc.strip()))

    return tools


def update_readme():
    """
    Update the tools section in readme.md
    """
    tools = get_tools()

    with open("readme.md", "r") as f:
        content = f.read()

    match = re.search(r"(### Tool use\n)(.*?)(\n#)", content, re.DOTALL)
    if not match:
        return

    prefix = match.group(1)
    body = match.group(2)
    suffix = match.group(3)

    new_body = ""
    for name, doc in tools:
        clean_doc = doc.split("\n")[0]
        new_body += f"- `{name}` - {clean_doc}\n"

    new_content = content[: match.start(2)] + new_body + content[match.end(2) :]

    with open("readme.md", "w") as f:
        f.write(new_content)


if __name__ == "__main__":
    update_readme()
