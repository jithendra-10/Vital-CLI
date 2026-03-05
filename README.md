# 🧠 Vital

> AI-powered coding assistant for your terminal — powered by Groq

## Installation

```bash
pip install vital
vital setup   # enter your Groq API key once
```

## Commands

| Command | What it does |
|---------|-------------|
| `vital chat <message>` | Chat with AI directly |
| `vital debug` | Debug errors with AI help |
| `vital explain <path>` | Explain code in plain English |
| `vital fix <file>` | Fix issues in a file |
| `vital doc <path>` | Generate documentation |
| `vital commit` | Auto-generate git commit messages |
| `vital refactor <file>` | Improve code quality |
| `vital test <file>` | Generate unit tests |
| `vital init <project>` | Create project boilerplate |

## Examples

```bash
# Debug an error
vital debug --run "python app.py"

# Explain your project
vital explain src/

# Fix a specific file
vital fix auth.py --issue "login fails for special characters"

# Generate docs
vital doc . --output README.md

# Smart commit
vital commit --push

# Generate tests
vital test main.py

# Start a new project
vital init flask-api --name my-project
```

## Requirements

- Python 3.10+
- Free [Groq API key](https://console.groq.com)

## License

MIT
