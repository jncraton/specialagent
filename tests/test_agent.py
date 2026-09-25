import importlib
import json
from copy import deepcopy
from unittest.mock import Mock


specialagent = importlib.import_module("specialagent.agent")


def recording_model(responses):
    """Create a mock call_model that snapshots each messages argument."""

    responses = list(responses)
    snapshots = []

    def call_model(messages, *args, **kwargs):
        snapshots.append(deepcopy(messages))
        return responses.pop(0)

    mock = Mock(side_effect=call_model)
    mock.snapshots = snapshots
    return mock


def test_quit_does_not_call_model_or_write_session(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    call_model = Mock()
    monkeypatch.setattr(specialagent, "call_model", call_model)

    specialagent.agent("/quit")

    call_model.assert_not_called()
    assert not (tmp_path / ".specialagent.last.session.json").exists()


def test_agent_returns_final_response(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    response = {
        "role": "assistant",
        "content": "The task is complete.",
    }

    call_model = recording_model([response])

    monkeypatch.setattr(specialagent, "call_model", call_model)
    monkeypatch.setattr(
        specialagent,
        "prefetch_sh",
        lambda cmd: [],
    )

    specialagent.agent("Do the task", system="test system")

    call_model.assert_called_once()

    assert call_model.snapshots[0] == [
        {
            "role": "system",
            "content": "test system",
        },
        {
            "role": "user",
            "content": "Do the task",
        },
    ]

    assert "LLM assistant message: The task is complete." in capsys.readouterr().out

    saved_messages = json.loads(
        (tmp_path / ".specialagent.last.session.json").read_text()
    )

    assert saved_messages == [
        {
            "role": "system",
            "content": "test system",
        },
        {
            "role": "user",
            "content": "Do the task",
        },
        response,
    ]


def test_agent_executes_tool_call_then_calls_model_again(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    first_response = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {
                    "name": "run_bash",
                    "arguments": json.dumps({"command": "echo hello"}),
                },
            }
        ],
    }

    final_response = {
        "role": "assistant",
        "content": "The command returned hello.",
    }

    call_model = recording_model(
        [
            first_response,
            final_response,
        ]
    )

    monkeypatch.setattr(specialagent, "call_model", call_model)
    monkeypatch.setattr(
        specialagent,
        "prefetch_sh",
        lambda cmd: [],
    )

    specialagent.agent("Run a command", system="system")

    assert call_model.call_count == 2

    assert call_model.snapshots[0] == [
        {
            "role": "system",
            "content": "system",
        },
        {
            "role": "user",
            "content": "Run a command",
        },
    ]

    assert call_model.snapshots[1] == [
        {
            "role": "system",
            "content": "system",
        },
        {
            "role": "user",
            "content": "Run a command",
        },
        first_response,
        {
            "role": "tool",
            "tool_call_id": "call-1",
            "content": "hello\n",
        },
    ]


def test_agent_executes_multiple_tool_calls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    response_with_tools = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "bash-call",
                "type": "function",
                "function": {
                    "name": "run_bash",
                    "arguments": json.dumps({"command": "echo one"}),
                },
            },
            {
                "id": "write-call",
                "type": "function",
                "function": {
                    "name": "write_file",
                    "arguments": json.dumps(
                        {
                            "filename": "output.txt",
                            "content": "hello",
                        }
                    ),
                },
            },
        ],
    }

    final_response = {
        "role": "assistant",
        "content": "Both tools completed.",
    }

    call_model = recording_model(
        [
            response_with_tools,
            final_response,
        ]
    )

    monkeypatch.setattr(specialagent, "call_model", call_model)
    monkeypatch.setattr(
        specialagent,
        "prefetch_sh",
        lambda cmd: [],
    )

    specialagent.agent("Use two tools", system="system")

    assert (tmp_path / "output.txt").read_text() == "hello"

    second_messages = call_model.snapshots[1]

    assert second_messages[-2:] == [
        {
            "role": "tool",
            "tool_call_id": "bash-call",
            "content": "one\n",
        },
        {
            "role": "tool",
            "tool_call_id": "write-call",
            "content": "Wrote to output.txt",
        },
    ]


def test_agent_passes_prefetched_messages_to_model(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    prefetched = [
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [],
        },
        {
            "role": "tool",
            "tool_call_id": "prefetch-1",
            "content": "file contents",
        },
    ]

    prefetch_sh = Mock(return_value=prefetched)
    monkeypatch.setattr(specialagent, "prefetch_sh", prefetch_sh)

    response = {
        "role": "assistant",
        "content": "Done.",
    }

    call_model = recording_model([response])
    monkeypatch.setattr(specialagent, "call_model", call_model)

    specialagent.agent("Inspect the project", system="system")

    assert prefetch_sh.called

    assert call_model.snapshots[0][2:4] == prefetched


def test_agent_uses_editor_when_prompt_is_empty(
    tmp_path,
    monkeypatch,
):
    monkeypatch.chdir(tmp_path)

    editor_input = Mock(return_value="prompt from editor")
    monkeypatch.setattr(specialagent, "editor_input", editor_input)
    monkeypatch.setattr(
        specialagent,
        "prefetch_sh",
        lambda cmd: [],
    )

    response = {
        "role": "assistant",
        "content": "Done.",
    }

    call_model = recording_model([response])
    monkeypatch.setattr(specialagent, "call_model", call_model)

    specialagent.agent("", system="system")

    editor_input.assert_called_once_with(".specialagent.last.prompt.txt")

    assert call_model.snapshots[0] == [
        {
            "role": "system",
            "content": "system",
        },
        {
            "role": "user",
            "content": "prompt from editor",
        },
    ]
