# Contributing

Thanks for helping. Every kind of contribution counts, and the most useful right now are listed first.

## Ways to help

1. **Try it on Windows** and tell us what happens, good or bad, in an [issue](https://github.com/abdelaalimouid/qgis-agent/issues/new/choose).
2. **Report a wrong result.** If an agent using the skill produced a number or a map that turned out to be wrong, that is the most valuable report there is: it becomes a test and a rule.
3. **Add an example** from your own area: the request you gave, the outputs, and how you checked them.
4. **Write a new skill** for a task on the [roadmap](ROADMAP.md).
5. **Translate** the README or the guide.

## Set up

You need QGIS (3 or 4) with its Python.

**Linux and macOS:** a conda-forge environment, or on macOS the QGIS app through the launcher:

```bash
mamba create -n qgis -c conda-forge qgis pytest
mamba activate qgis
# or, with the QGIS app on macOS:
bash skills/qgis-agent/scripts/qgis_python.sh -m pytest
```

**Windows:** the official QGIS installer, through its own Python launcher (this is what the Windows tests use):

```bat
"C:\Program Files\QGIS 3.44.15\bin\python-qgis-ltr.bat" -m pip install pytest
"C:\Program Files\QGIS 3.44.15\bin\python-qgis-ltr.bat" -m pytest
```

## Run the tests

```bash
python -m pytest                          # offline tests, about 10 seconds
QGIS_AGENT_LIVE=1 python -m pytest        # also downloads real Sentinel-2 data
```

The same offline tests run automatically on Linux, macOS and Windows for every push and pull request.

## Rules for changes

- **Prove it.** A new script or recipe comes with a test that compares its result with an independent calculation (numpy, a known value, a reference file). A result that only "looks right" is not enough: that is how silent errors get through.
- **Keep the method.** Plan before acting, QGIS's own tools where the user can redo the step by hand, checks before handing over, no figure the processing did not produce.
- **Plain English** in the docs: short sentences, concrete words, real examples.
- **Update [CHANGELOG.md](CHANGELOG.md)** under "Unreleased".
- Keep version numbers in `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `CITATION.cff` and the README in sync; a test checks it.

## Adding a skill

A skill is a folder under `skills/` with a `SKILL.md` (front matter `name` and `description`, then the instructions), plus optional `scripts/`, `references/` and `assets/`. Keep `SKILL.md` short and put details in references. Describe in `description` when the skill should be used, since that is what makes Claude pick it.

## Pull requests

Small and focused is best. Describe what changed, how you tested it, and link the issue it closes.
