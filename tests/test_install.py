import json
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "install.sh"
BEGIN = "<!-- claude-output-style:begin -->"
END = "<!-- claude-output-style:end -->"
BLOCK = (REPO / "CLAUDE.md").read_text(encoding="utf-8")


def run(home: Path, *args: str, config_dir: Path | None = None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CONFIG_DIR"}
    env["HOME"] = str(home)
    if config_dir:
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    return subprocess.run(
        ["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True, check=False
    )


@pytest.fixture
def home(tmp_path: Path) -> Path:
    (tmp_path / ".claude").mkdir()
    return tmp_path


def claude_md(home: Path) -> Path:
    return home / ".claude" / "CLAUDE.md"


def backups(home: Path, name: str = "CLAUDE.md") -> list[Path]:
    return sorted((home / ".claude").glob(f"{name}.bak-*"))


class TestInstall:
    def test_creates_file_when_missing(self, home: Path) -> None:
        result = run(home)
        assert result.returncode == 0, result.stderr
        assert claude_md(home).read_text() == BLOCK
        assert backups(home) == []

    def test_creates_claude_dir_when_missing(self, tmp_path: Path) -> None:
        result = run(tmp_path)
        assert result.returncode == 0, result.stderr
        assert claude_md(tmp_path).read_text() == BLOCK

    def test_appends_after_existing_content_and_backs_up(self, home: Path) -> None:
        original = "# Mine\n\n- rule one\n"
        claude_md(home).write_text(original)
        assert run(home).returncode == 0
        assert claude_md(home).read_text() == original + "\n" + BLOCK
        [backup] = backups(home)
        assert backup.read_text() == original

    def test_existing_file_without_trailing_newline(self, home: Path) -> None:
        claude_md(home).write_text("# Mine")
        assert run(home).returncode == 0
        assert claude_md(home).read_text() == "# Mine\n\n" + BLOCK

    def test_second_run_is_noop(self, home: Path) -> None:
        claude_md(home).write_text("# Mine\n")
        run(home)
        after_first = claude_md(home).read_text()
        result = run(home)
        assert result.returncode == 0
        assert claude_md(home).read_text() == after_first
        assert after_first.count(BEGIN) == 1
        assert len(backups(home)) == 1
        assert "up to date" in result.stdout

    def test_replaces_outdated_block_in_place(self, home: Path) -> None:
        claude_md(home).write_text(f"top\n\n{BEGIN}\nold rules\n{END}\n\nbottom\n")
        assert run(home).returncode == 0
        assert claude_md(home).read_text() == f"top\n\n{BLOCK}\nbottom\n"

    def test_keeps_file_mode(self, home: Path) -> None:
        claude_md(home).write_text("x\n")
        claude_md(home).chmod(0o600)
        run(home)
        assert claude_md(home).stat().st_mode & 0o777 == 0o600

    def test_symlinked_file_stays_a_symlink(self, home: Path, tmp_path: Path) -> None:
        real = tmp_path / "dotfiles" / "CLAUDE.md"
        real.parent.mkdir()
        real.write_text("# Mine\n")
        claude_md(home).symlink_to(real)
        assert run(home).returncode == 0
        assert claude_md(home).is_symlink()
        assert real.read_text() == "# Mine\n\n" + BLOCK

    @pytest.mark.parametrize(
        "content",
        [
            f"a\n{BEGIN}\nno end\n",
            f"a\n{END}\nno begin\n",
            f"{END}\nx\n{BEGIN}\n",
            f"{BEGIN}\n{END}\n{BEGIN}\n{END}\n",
        ],
    )
    def test_broken_markers_abort_without_changes(self, home: Path, content: str) -> None:
        claude_md(home).write_text(content)
        result = run(home)
        assert result.returncode == 1
        assert "markers" in result.stderr
        assert claude_md(home).read_text() == content
        assert backups(home) == []

    def test_marker_text_inside_a_line_is_not_a_marker(self, home: Path) -> None:
        original = f"see `{BEGIN}` in docs\n"
        claude_md(home).write_text(original)
        assert run(home).returncode == 0
        assert claude_md(home).read_text() == original + "\n" + BLOCK

    def test_respects_claude_config_dir(self, home: Path, tmp_path: Path) -> None:
        config = tmp_path / "cfg"
        assert run(home, config_dir=config).returncode == 0
        assert (config / "CLAUDE.md").read_text() == BLOCK
        assert not claude_md(home).exists()

    def test_unknown_option(self, home: Path) -> None:
        result = run(home, "--bogus")
        assert result.returncode == 2
        assert not claude_md(home).exists()


class TestUninstall:
    def test_roundtrip_restores_original(self, home: Path) -> None:
        original = "# Mine\n\n- rule\n\n\n- after blank lines\n"
        claude_md(home).write_text(original)
        run(home)
        result = run(home, "--uninstall")
        assert result.returncode == 0, result.stderr
        assert claude_md(home).read_text() == original

    def test_removes_block_from_middle(self, home: Path) -> None:
        claude_md(home).write_text(f"top\n\n{BEGIN}\nold\n{END}\n\nbottom\n")
        assert run(home, "--uninstall").returncode == 0
        assert claude_md(home).read_text() == "top\n\nbottom\n"

    def test_not_installed_is_noop(self, home: Path) -> None:
        claude_md(home).write_text("# Mine\n")
        result = run(home, "--uninstall")
        assert result.returncode == 0
        assert claude_md(home).read_text() == "# Mine\n"
        assert backups(home) == []

    def test_missing_file_is_noop(self, home: Path) -> None:
        assert run(home, "--uninstall").returncode == 0
        assert not claude_md(home).exists()

    def test_broken_markers_abort(self, home: Path) -> None:
        content = f"a\n{BEGIN}\n"
        claude_md(home).write_text(content)
        assert run(home, "--uninstall").returncode == 1
        assert claude_md(home).read_text() == content


class TestOutputStyleSetting:
    def _settings(self, home: Path, name: str, data: dict) -> Path:
        path = home / ".claude" / name
        path.write_text(json.dumps(data, indent=2))
        return path

    def test_removes_foreign_style_and_keeps_other_keys(self, home: Path) -> None:
        path = self._settings(home, "settings.local.json", {"outputStyle": "humanized", "x": 1})
        result = run(home)
        assert result.returncode == 0
        assert json.loads(path.read_text()) == {"x": 1}
        [backup] = backups(home, "settings.local.json")
        assert json.loads(backup.read_text())["outputStyle"] == "humanized"
        assert "humanized" in result.stdout

    def test_checks_both_settings_files(self, home: Path) -> None:
        a = self._settings(home, "settings.json", {"outputStyle": "Explanatory"})
        b = self._settings(home, "settings.local.json", {"outputStyle": "humanized"})
        run(home)
        assert json.loads(a.read_text()) == {}
        assert json.loads(b.read_text()) == {}

    @pytest.mark.parametrize("style", ["plain", "default"])
    def test_own_or_default_style_untouched(self, home: Path, style: str) -> None:
        path = self._settings(home, "settings.json", {"outputStyle": style})
        before = path.read_text()
        run(home)
        assert path.read_text() == before
        assert backups(home, "settings.json") == []

    def test_keep_style_flag(self, home: Path) -> None:
        path = self._settings(home, "settings.json", {"outputStyle": "humanized"})
        before = path.read_text()
        result = run(home, "--keep-style")
        assert result.returncode == 0
        assert path.read_text() == before
        assert "humanized" in result.stdout

    def test_invalid_json_left_alone(self, home: Path) -> None:
        path = home / ".claude" / "settings.json"
        path.write_text("{ not json")
        result = run(home)
        assert result.returncode == 0
        assert path.read_text() == "{ not json"
        assert claude_md(home).read_text() == BLOCK

    def test_uninstall_does_not_touch_settings(self, home: Path) -> None:
        path = self._settings(home, "settings.json", {"outputStyle": "humanized"})
        before = path.read_text()
        run(home, "--uninstall")
        assert path.read_text() == before


class TestStyleFile:
    def test_with_style_copies_file(self, home: Path) -> None:
        assert run(home, "--with-style").returncode == 0
        installed = home / ".claude/output-styles/plain.md"
        assert installed.read_text() == (REPO / "output-styles/plain.md").read_text()

    def test_without_flag_no_style_file(self, home: Path) -> None:
        run(home)
        assert not (home / ".claude/output-styles/plain.md").exists()

    def test_uninstall_removes_unmodified_style(self, home: Path) -> None:
        run(home, "--with-style")
        run(home, "--uninstall")
        assert not (home / ".claude/output-styles/plain.md").exists()

    def test_uninstall_keeps_modified_style(self, home: Path) -> None:
        run(home, "--with-style")
        style = home / ".claude/output-styles/plain.md"
        style.write_text("my edits")
        result = run(home, "--uninstall")
        assert style.read_text() == "my edits"
        assert "modified" in result.stdout
