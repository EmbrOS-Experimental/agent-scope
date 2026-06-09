# Contributing to AgentScope

Thanks for your interest! Here's how to contribute:

## Setup

```bash
git clone https://github.com/kodesweb3/agent-scope.git
cd agent-scope
pip install -e ".[dev]"
```

## Running Tests

```bash
python3 -m pytest tests/ -v
```

All 56 tests must pass before submitting a PR.

## Code Style

```bash
ruff check agentscope/
mypy agentscope/
```

## Project Structure

```
agentscope/
├── core/
│   ├── models.py      # Pydantic data models
│   ├── emitter.py     # Main capture SDK
│   ├── store.py       # Cross-platform trace storage
│   └── redaction.py   # Secret detection & redaction
├── cli/
│   └── main.py        # Click-based CLI
├── adapters/
│   └── shims.py       # Agent adapter framework
└── tests/             # 56 tests, all passing
```

## Adding an Adapter

1. Subclass the adapter pattern in `adapters/shims.py`
2. Add tests in `tests/test_adapters.py`
3. Update the README adapters table
