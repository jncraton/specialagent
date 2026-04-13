# specialagent

A minimalist autonomous agent

[![Lint](https://github.com/jncraton/specialagent/actions/workflows/lint.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/lint.yml)
[![Test](https://github.com/jncraton/specialagent/actions/workflows/test.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/test.yml)
[![Deploy](https://github.com/jncraton/specialagent/actions/workflows/deploy.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/deploy.yml)
[![Release](https://github.com/jncraton/specialagent/actions/workflows/release.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/release.yml)
[![PyPI](https://github.com/jncraton/specialagent/actions/workflows/pypi.yml/badge.svg)](https://github.com/jncraton/specialagent/actions/workflows/pypi.yml)

## Features

- Function calling for shell access and file operations
- Zero-dependency Python implementation

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

```sh
export GEMINI_API_KEY='your-api-key-here'
```
