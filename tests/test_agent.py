import importlib
import json
from copy import deepcopy
from unittest.mock import Mock

specialagent = importlib.import_module("specialagent.agent")

mock_tools = {
    "role": "assistant",
    "content": None,
    "tool_calls": [
        {
            "id": "1",
            "type": "function",
            "function": {
                "name": "exec",
                "arguments": '{"command": "echo 1"}',
            },
        }
    ],
}


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

    call_model = recording_model([{"role": "assistant", "content": "done"}])

    monkeypatch.setattr(specialagent, "call_model", call_model)
    monkeypatch.setattr(specialagent, "prefetch_sh", lambda cmd: mock_tools)

    specialagent.agent("p", system="s")

    call_model.assert_called_once()

    assert call_model.snapshots[0][:2] == [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "p"},
    ]

    assert "done" in capsys.readouterr().out

    saved_messages = json.loads(
        (tmp_path / ".specialagent.last.session.json").read_text()
    )

    assert saved_messages == call_model.snapshots[0] + [
        {"role": "assistant", "content": "done"}
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
                "id": "1",
                "type": "function",
                "function": {
                    "name": "exec",
                    "arguments": json.dumps({"command": "echo hello"}),
                },
            }
        ],
    }

    final_response = {"role": "assistant", "content": "The command returned hello."}

    call_model = recording_model([first_response, final_response])

    monkeypatch.setattr(specialagent, "call_model", call_model)
    monkeypatch.setattr(specialagent, "prefetch_sh", lambda cmd: mock_tools)

    specialagent.agent("p", system="s")

    assert call_model.call_count == 2

    assert call_model.snapshots[0][:2] == [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "p"},
    ]

    assert call_model.snapshots[1] == call_model.snapshots[0] + [
        first_response,
        {"role": "tool", "tool_call_id": "1", "content": "hello"},
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
                    "name": "exec",
                    "arguments": json.dumps({"command": "echo one"}),
                },
            },
            {
                "id": "write-call",
                "type": "function",
                "function": {
                    "name": "writeFile",
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

    final_response = {"role": "assistant", "content": "done"}

    call_model = recording_model([response_with_tools, final_response])

    monkeypatch.setattr(specialagent, "call_model", call_model)
    monkeypatch.setattr(specialagent, "prefetch_sh", lambda cmd: mock_tools)

    specialagent.agent("p", system="s")

    assert (tmp_path / "output.txt").read_text() == "hello"

    assert call_model.snapshots[1][-2:] == [
        {
            "role": "tool",
            "tool_call_id": "bash-call",
            "content": "one",
        },
        {
            "role": "tool",
            "tool_call_id": "write-call",
            "content": None,
        },
    ]


def test_agent_passes_prefetched_messages_to_model(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(specialagent, "prefetch_sh", lambda cmd: mock_tools)

    response = {
        "role": "assistant",
        "content": "Done.",
    }

    call_model = recording_model([response])
    monkeypatch.setattr(specialagent, "call_model", call_model)

    specialagent.agent("Inspect the project", system="system")

    assert len(call_model.snapshots[0]) == 4


def test_agent_uses_editor_when_prompt_is_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    editor_input = Mock(return_value="prompt from editor")
    monkeypatch.setattr(specialagent, "editor_input", editor_input)
    monkeypatch.setattr(specialagent, "prefetch_sh", lambda cmd: mock_tools)

    call_model = recording_model([{"role": "assistant", "content": "done"}])
    monkeypatch.setattr(specialagent, "call_model", call_model)

    specialagent.agent("", system="system")

    editor_input.assert_called_once_with(".specialagent.last.prompt.txt")

    assert call_model.snapshots[0][:2] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "prompt from editor"},
    ]
