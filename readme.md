# specialagent

[![Lint](https://github.com/jncraton/specialagent/actions/workflows/lint.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/lint.yml)
[![Test](https://github.com/jncraton/specialagent/actions/workflows/test.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/test.yml)
[![Deploy](https://github.com/jncraton/specialagent/actions/workflows/deploy.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/deploy.yml)
[![Release](https://github.com/jncraton/specialagent/actions/workflows/release.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/release.yml)
[![PyPI](https://github.com/jncraton/specialagent/actions/workflows/pypi.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/pypi.yml)

A minimalist [LLM](https://en.wikipedia.org/wiki/Large_language_model)-driven [agent](https://en.wikipedia.org/wiki/Intelligent_agent)

> An agent is just something that acts (agent comes from the Latin [agere](https://en.wiktionary.org/wiki/ago#Verb), to do). Of course, all computer programs do something, but computer agents are expected to do more: operate autonomously, perceive their environment, persist over a prolonged time period, adapt to change, and create and pursue goals.
>
> [Russel & Norvig, 1995](https://en.wikipedia.org/wiki/Artificial_Intelligence:_A_Modern_Approach)

Designed with educational use in mind, this agent harness is intentionally only a few hundred lines of readable, dependency-free Python. It acts on its environment by running shell commands and receives output of those commands as percepts to drive subsequent actions.

![Agent Diagram](https://upload.wikimedia.org/wikipedia/commons/3/3f/IntelligentAgent-SimpleReflex.png)

## Features

- Tool use. The agent has 4 tools:
  - `exec` - Run `bash` commands
  - `write` - Overwrites the contents of a file
  - `replace` - Find and replace in file
  - `read_skill` - Load a skill file
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

In its default configuration, the agent will attempt to use the model hosted at `http://127.0.0.1:8080/v1/chat/completions` (the llama.cpp default). Alternatives may be provided by env variables. For example, to use Gemma 4 31B hosted on AI Studio:

```sh
export LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
export LLM_API_KEY=your-api-key-here
export LLM_MODEL=gemma-4-31b-it
```
