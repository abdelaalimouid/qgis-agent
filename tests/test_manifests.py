"""Release hygiene: manifests parse, the skill's front matter is valid, and every version number agrees."""
import json
import re

from conftest import ROOT

PLUGIN = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
MARKET = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))


def test_skill_front_matter():
    text = (ROOT / "skills" / "qgis-agent" / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n---\n", text, re.S)
    assert m, "SKILL.md must start with name and description front matter"
    assert m.group(1) == "qgis-agent"
    assert 50 < len(m.group(2)) <= 1024


def test_skill_name_follows_the_agent_skills_format():
    """Claude Code and Codex both read skills in the open Agent Skills format: the name must match the folder,
    use lowercase letters, digits and hyphens, and stay within 64 characters."""
    folder = ROOT / "skills" / "qgis-agent"
    name = re.search(r"^name: (.+)$", (folder / "SKILL.md").read_text(encoding="utf-8"), re.M).group(1).strip()
    assert name == folder.name
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) and len(name) <= 64


def test_versions_agree():
    version = PLUGIN["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert [p["version"] for p in MARKET["plugins"] if p["name"] == "qgis-agent"] == [version]
    assert f"version: {version}" in (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    assert f"(version {version})" in (ROOT / "README.md").read_text(encoding="utf-8")
    assert f"## [{version}]" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_skill_files_referenced_in_skill_md_exist():
    text = (ROOT / "skills" / "qgis-agent" / "SKILL.md").read_text(encoding="utf-8")
    for rel in set(re.findall(r"`((?:scripts|references|assets)/[\w.\-]+)`", text)):
        assert (ROOT / "skills" / "qgis-agent" / rel).exists(), rel
