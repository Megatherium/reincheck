# reincheck - just a simple personal tool to keep my agents uptodate

## Tech & Important Steps

We're using Python with Pyenv and uv as a package manager

- When running anything python just do a `uv venv` beforehand
- DO NOT use pip directly but rather `uv pip install <mypackage>`

## Task

Currently I have the following agents installed:

- Crush
- Kilocode
- Opencode
- Claude
- Grok-cli
- Gemini-cli
- Aider
- open-interpreter

That list is open to change. For every agent you need to research three things:

- The command to show the installed version
- The command to find out the newest version (if this not a simple curl|grep and you need to write some code: that's ok)
- The command to upgrade the agent.
- Maybe also make a field for the newest released version so we don't have to recheck every time but still know there's a update waiting.

## Implementation details

Use YAML for the config file and Click for the CLI commands.
The config file is really just a list of dicts to represent the needed things.
We need a check command that will check if an agent has a new version (or all agents if no argument is supplied)
Same goes for upgrade: upgrade all when no argument is given.

You should find all the agents in my PATH. You can run check but NEVER run an upgrade command. I will check all your data before doing anything potentially dangerous.
