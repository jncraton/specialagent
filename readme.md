# specialagent

A minimalist [LLM](https://en.wikipedia.org/wiki/Large_language_model)-driven [agent](https://en.wikipedia.org/wiki/Intelligent_agent)

[![Lint](https://github.com/jncraton/specialagent/actions/workflows/lint.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/lint.yml)
[![Test](https://github.com/jncraton/specialagent/actions/workflows/test.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/test.yml)
[![Deploy](https://github.com/jncraton/specialagent/actions/workflows/deploy.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/deploy.yml)
[![Release](https://github.com/jncraton/specialagent/actions/workflows/release.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/release.yml)
[![PyPI](https://github.com/jncraton/specialagent/actions/workflows/pypi.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/pypi.yml)

Designed with educational use in mind, this agent harness is intentionally only a few hundred lines of readable, dependency-free Python.

![Agent Diagram](https://upload.wikimedia.org/wikipedia/commons/3/3f/IntelligentAgent-SimpleReflex.png)

## Features

- Tool use. The agent has 4 tools:
  - `exec` - Run `bash` commands
  - `write` - Overwrites the contents of a file
  - `replace` - Find and replace in file
  - `exit` - Terminate session

## Security

This package allows LLMs to directly execute shell commands. It should never be used without appropriate sandboxing.
## Usage

```sh
uvx specialagent
```

or

```sh
pipx specialagent
```

## Configuration

In its default configuration, the agent will attempt to use the default model hosted at `http://127.0.0.1:8080/v1/chat/completions` (the llama.cpp default). If a Gemini key is provided, the agent will instead use Gemma 4 31B hosted on AI Studio.

```sh
export GEMINI_API_KEY='your-api-key-here'
```
