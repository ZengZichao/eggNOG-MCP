# Contributing to eggNOG-MCP

Thank you for your interest in contributing to eggNOG-MCP! This is a community-maintained, unofficial MCP server for the eggNOG database.

## How to Contribute

### Reporting Issues

- Use the [GitHub Issues](https://github.com/ZengZichao/eggNOG-MCP/issues) page to report bugs or request features.
- Before creating a new issue, please search existing issues to avoid duplicates.
- When reporting a bug, include:
  - A clear description of the problem
  - Steps to reproduce
  - Expected vs. actual behavior
  - Python version, MCP SDK version, and OS

### Pull Requests

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes.
4. Run tests and linting:
   ```bash
   pytest tests/ -v
   ruff check src/
   ruff format --check src/
   ```
5. Commit with a clear message.
6. Push to your fork and submit a pull request.

### Code Style

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guidelines.
- Use `ruff` for linting and formatting (line length: 100).
- Write clear docstrings for all public functions and classes.
- Add type annotations to all function signatures.

### Testing

- All new features should include unit tests in the `tests/` directory.
- Use `pytest` and `pytest-asyncio` for async test cases.
- Mock external HTTP calls — do not hit the real eggNOG server in tests.

## Development Setup

```bash
git clone https://github.com/ZengZichao/eggNOG-MCP.git
cd eggNOG-MCP
pip install -e ".[dev]"
```

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](./LICENSE).

## Code of Conduct

Be respectful and constructive in all interactions. We welcome contributors of all backgrounds and skill levels.
