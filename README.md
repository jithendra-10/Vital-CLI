# ⚡ Vital — AI-Powered Terminal Coding Assistant

<p align="center">
  <img src="https://img.shields.io/pypi/v/vital-cli?color=00ffcc&label=version&style=flat-square" alt="PyPI Version">
  <img src="https://img.shields.io/pypi/pyversions/vital-cli?style=flat-square" alt="Python Versions">
  <img src="https://img.shields.io/pypi/l/vital-cli?style=flat-square" alt="License">
  <img src="https://img.shields.io/pypi/dm/vital-cli?style=flat-square&color=ffdd57" alt="Downloads">
</p>

<p align="center">
  <b>Build, debug, refactor and ship code faster — all from your terminal.</b><br>
  Powered by your choice of AI: Groq, OpenAI, Claude, or Gemini.
</p>

---

## 🚀 Install

```bash
pip install vital-cli
```

Then run:

```bash
vital
```

That's it. No config files, no setup scripts — just run `vital` and go.

---

## ✨ Features

### 🤖 Multi-Provider AI Support
Use any combination of AI providers you have keys for:
- **Groq** — Ultra-fast, free tier available
- **OpenAI** — GPT-4o for complex reasoning
- **Anthropic** — Claude for code review and quality
- **Google** — Gemini for large context tasks

```bash
vital setup   # add your API keys
vital status  # see what's configured
```

### 🧠 Agent Mode — Build Full Projects Automatically
Just describe what you want. Vital plans, builds, runs and fixes it:

```bash
vital › build me a flask todo app with login
```

Vital will:
1. Plan all files needed
2. Generate each file completely
3. Install dependencies
4. Run and test the project
5. Auto-fix any errors found

### 💬 Interactive Mode with Memory
Vital remembers your conversation and project preferences:

```bash
vital                          # launch interactive mode
vital --resume                 # resume last session
```

Inside Vital:
```
vital › create a calculator with html css js
vital › now add dark mode to it       ← remembers context
vital › make the buttons bigger       ← still remembers
```

### 📁 Project Memory (VITAL.md)
Rules that persist across every session:

```
/memory init                    create VITAL.md for this project
/memory add "always use TypeScript"
/memory add --global "I prefer Flask over Django"
/memory show                    see what Vital remembers
```

### 🛠️ Powerful Commands

| Command | What it does |
|---------|-------------|
| `vital debug` | Analyze errors and suggest fixes |
| `vital fix <file>` | Fix issues in a file using AI |
| `vital refactor <file>` | Improve code quality |
| `vital test <file>` | Generate unit tests |
| `vital doc <path>` | Generate documentation |
| `vital commit` | Auto-generate git commit messages |
| `vital explain <file>` | Explain code in plain English |
| `vital init <type>` | Generate project boilerplate |
| `vital agent "build X"` | Full autonomous project builder |

---

## ⚙️ Setup

### Basic (Groq only — free tier available)
```bash
pip install vital-cli
vital setup
# Enter your Groq API key from console.groq.com
vital
```

### With all providers
```bash
pip install "vital-cli[all]"
vital setup
# Add any keys you have — skip ones you don't
```

### Install specific providers
```bash
pip install "vital-cli[openai]"     # + OpenAI
pip install "vital-cli[anthropic]"  # + Claude
pip install "vital-cli[gemini]"     # + Gemini
pip install "vital-cli[all]"        # everything
```

---

## 🎮 Usage

### Interactive Mode
```bash
vital                    # start
vital --resume           # resume last session
vital --version          # show version
```

### Inside Vital — Slash Commands
```
/help          show all commands
/memory init   create project memory file
/memory add    add a rule to memory
/history       show session history
/resume        load a previous session
/providers     manage your AI providers
/agent         launch agent mode
/context       show project context
/clear         clear screen
/exit          quit
```

### Direct Commands
```bash
vital debug --file app.py
vital debug --error "TypeError: cannot read..."
vital fix app.py --issue "function returns wrong value"
vital refactor app.py
vital test app.py
vital doc .
vital commit --push
vital explain app.py --simple
vital init flask-api --name myproject
vital agent "a react weather app"
```

---

## 🏗️ Project Structure

After `pip install vital-cli`, your project can use a `VITAL.md` file for persistent memory:

```markdown
# Vital Project Memory
## Coding Rules
- Always use TypeScript
- Use Tailwind CSS for styling
- Follow REST API conventions
```

Vital reads this automatically every session — no need to repeat yourself.

---

## 🔑 Getting API Keys

| Provider | Free Tier | Get Key |
|----------|-----------|---------|
| Groq | ✅ Yes | [console.groq.com](https://console.groq.com) |
| OpenAI | ❌ Paid | [platform.openai.com](https://platform.openai.com) |
| Anthropic | ❌ Paid | [console.anthropic.com](https://console.anthropic.com) |
| Google Gemini | ✅ Yes | [aistudio.google.com](https://aistudio.google.com) |

**Recommended for beginners:** Start with Groq — it's free, fast, and works great.

---

## 🤝 Contributing

```bash
git clone https://github.com/yourusername/Vital-CLI
cd Vital-CLI
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e ".[all]"
vital
```

Pull requests welcome! Check the issues page for things to work on.

---

## 📄 License

MIT License — free to use, modify and distribute.

---

<p align="center">
  Built with ❤️ for developers who live in the terminal.
</p>