import json
import subprocess
from pathlib import Path

import pytest

import bench.run as run_module
from bench.run import (
    Job,
    Variant,
    build_command,
    build_settings,
    clean_env,
    load_variants,
    make_home,
    parse_turn,
    style_name,
    sync_credentials,
)


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _write(root / "CLAUDE.md", "rules")
    _write(root / "output-styles/plain.md", "---\nname: plain\n---\nbody")
    _write(
        root / "variants.json",
        json.dumps(
            {
                "settings": {"language": "Russian"},
                "variants": {
                    "baseline": {},
                    "md": {"claude_md": "CLAUDE.md"},
                    "st": {
                        "style": "output-styles/plain.md",
                        "settings": {"effortLevel": "low", "language": "English"},
                    },
                    "missing": {"claude_md": "nope.md"},
                    "multi": {"claude_md": ["CLAUDE.md", "extra.md"]},
                    "nolang": {"settings": {"language": None}},
                    "sp": {"system_prompt": ["CLAUDE.md", "extra.md"]},
                },
            }
        ),
    )
    _write(root / "extra.md", "more rules")
    return root


class TestLoadVariants:
    def test_resolves_relative_paths_against_repo(self, repo: Path) -> None:
        [md] = load_variants(repo / "variants.json", ["md"], repo)
        assert md.claude_md == (repo / "CLAUDE.md",)
        assert md.style is None

    def test_keeps_requested_order(self, repo: Path) -> None:
        names = [v.name for v in load_variants(repo / "variants.json", ["st", "baseline"], repo)]
        assert names == ["st", "baseline"]

    def test_merges_base_and_variant_settings(self, repo: Path) -> None:
        [st] = load_variants(repo / "variants.json", ["st"], repo)
        assert st.settings == {"language": "English", "effortLevel": "low"}

    def test_unknown_variant_raises(self, repo: Path) -> None:
        with pytest.raises(ValueError, match="nope"):
            load_variants(repo / "variants.json", ["nope"], repo)

    def test_missing_file_raises(self, repo: Path) -> None:
        with pytest.raises(FileNotFoundError, match=r"nope\.md"):
            load_variants(repo / "variants.json", ["missing"], repo)

    def test_missing_file_in_unrequested_variant_is_ignored(self, repo: Path) -> None:
        assert len(load_variants(repo / "variants.json", ["baseline"], repo)) == 1


class TestVariantExtras:
    def test_claude_md_list_resolves_every_file(self, repo: Path) -> None:
        [v] = load_variants(repo / "variants.json", ["multi"], repo)
        assert v.claude_md == (repo / "CLAUDE.md", repo / "extra.md")

    def test_null_setting_removes_base_key(self, repo: Path) -> None:
        [v] = load_variants(repo / "variants.json", ["nolang"], repo)
        assert "language" not in v.settings

    def test_make_home_concatenates_claude_md_files(self, repo: Path, tmp_path: Path) -> None:
        creds = _write(tmp_path / "real/.credentials.json", "{}")
        [v] = load_variants(repo / "variants.json", ["multi"], repo)
        home, _ = make_home(tmp_path / "job", v, creds)
        assert (home / ".claude/CLAUDE.md").read_text() == "rules\n\nmore rules"


class TestSystemPrompt:
    def test_make_home_writes_concatenated_system_prompt(self, repo: Path, tmp_path: Path) -> None:
        creds = _write(tmp_path / "real/.credentials.json", "{}")
        [v] = load_variants(repo / "variants.json", ["sp"], repo)
        home, _ = make_home(tmp_path / "job", v, creds)
        assert (home / "system-prompt.md").read_text() == "rules\n\nmore rules"

    def test_no_system_prompt_file_without_setting(self, repo: Path, tmp_path: Path) -> None:
        creds = _write(tmp_path / "real/.credentials.json", "{}")
        [v] = load_variants(repo / "variants.json", ["baseline"], repo)
        home, _ = make_home(tmp_path / "job", v, creds)
        assert not (home / "system-prompt.md").exists()


class TestStyleName:
    def test_reads_frontmatter_name(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "file.md", "---\ndescription: x\nname: Plain Talk\n---\nbody")
        assert style_name(path) == "Plain Talk"

    def test_falls_back_to_stem(self, tmp_path: Path) -> None:
        assert style_name(_write(tmp_path / "terse.md", "no frontmatter")) == "terse"

    def test_name_outside_frontmatter_ignored(self, tmp_path: Path) -> None:
        text = "---\ndescription: x\n---\nname: fake\n"
        assert style_name(_write(tmp_path / "terse.md", text)) == "terse"


class TestBuildSettings:
    def test_adds_output_style_for_style_variant(self, repo: Path) -> None:
        [st] = load_variants(repo / "variants.json", ["st"], repo)
        assert build_settings(st)["outputStyle"] == "plain"

    def test_no_output_style_without_style(self, repo: Path) -> None:
        [md] = load_variants(repo / "variants.json", ["md"], repo)
        assert "outputStyle" not in build_settings(md)


class TestBuildCommand:
    def _variant(self, **kw: object) -> Variant:
        base = {
            "name": "v",
            "claude_md": None,
            "style": None,
            "system_prompt": None,
            "settings": {},
        }
        return Variant(**{**base, **kw})  # type: ignore[arg-type]

    def test_prompt_directly_after_print_flag(self) -> None:
        cmd = build_command("какой порт", self._variant(), None)
        assert cmd[:3] == ["claude", "-p", "какой порт"]

    def test_isolation_flags(self) -> None:
        cmd = build_command("q", self._variant(), None)
        assert "--strict-mcp-config" in cmd
        assert cmd[cmd.index("--tools") + 1] == ""
        assert cmd[cmd.index("--output-format") + 1] == "json"

    def test_variadic_tools_flag_is_not_last(self) -> None:
        cmd = build_command("q", self._variant(), None)
        assert cmd.index("--tools") + 1 < len(cmd) - 1

    def test_resume_added_only_when_given(self) -> None:
        assert "--resume" not in build_command("q", self._variant(), None)
        cmd = build_command("q", self._variant(), "sid-1")
        assert cmd[cmd.index("--resume") + 1] == "sid-1"

    def test_system_prompt_file(self, tmp_path: Path) -> None:
        sp = tmp_path / "prefs.md"
        cmd = build_command("q", self._variant(), None, sp)
        assert cmd[cmd.index("--system-prompt-file") + 1] == str(sp)

    def test_no_system_prompt_flag_by_default(self) -> None:
        assert "--system-prompt-file" not in build_command("q", self._variant(), None)


class TestMakeHome:
    def test_layout(self, repo: Path, tmp_path: Path) -> None:
        creds = _write(tmp_path / "real/.credentials.json", "{}")
        [v] = load_variants(repo / "variants.json", ["st"], repo)
        v = Variant(**{**v.__dict__, "claude_md": (repo / "CLAUDE.md",)})
        home, cwd = make_home(tmp_path / "job", v, creds)
        link = home / ".claude/.credentials.json"
        assert link.is_symlink() and link.resolve() == creds.resolve()
        assert (home / ".claude/CLAUDE.md").read_text() == "rules"
        assert (home / ".claude/output-styles/plain.md").exists()
        trust = json.loads((home / ".claude.json").read_text())
        assert trust["projects"][str(cwd)]["hasTrustDialogAccepted"] is True
        assert cwd.is_dir()

    def test_baseline_has_no_rules(self, repo: Path, tmp_path: Path) -> None:
        creds = _write(tmp_path / "real/.credentials.json", "{}")
        [v] = load_variants(repo / "variants.json", ["baseline"], repo)
        home, _ = make_home(tmp_path / "job", v, creds)
        assert not (home / ".claude/CLAUDE.md").exists()
        assert not (home / ".claude/output-styles").exists()


class TestSyncCredentials:
    def _setup(self, tmp_path: Path) -> tuple[Path, Path]:
        real = _write(tmp_path / "real/.credentials.json", "old")
        link = tmp_path / "home/.claude/.credentials.json"
        link.parent.mkdir(parents=True)
        link.symlink_to(real)
        return real, link

    def test_intact_symlink_does_nothing(self, tmp_path: Path) -> None:
        real, _ = self._setup(tmp_path)
        assert sync_credentials(tmp_path / "home", real) is None
        assert real.read_text() == "old"

    def test_replaced_file_with_new_token_is_copied_back(self, tmp_path: Path) -> None:
        real, link = self._setup(tmp_path)
        link.unlink()
        link.write_text("new")
        warning = sync_credentials(tmp_path / "home", real)
        assert warning is not None
        assert real.read_text() == "new"
        assert real.stat().st_mode & 0o777 == 0o600

    def test_replaced_file_with_same_content_not_written(self, tmp_path: Path) -> None:
        real, link = self._setup(tmp_path)
        link.unlink()
        link.write_text("old")
        mtime = real.stat().st_mtime_ns
        assert sync_credentials(tmp_path / "home", real) is None
        assert real.stat().st_mtime_ns == mtime

    def test_symlinked_real_credentials_updated_through_link(self, tmp_path: Path) -> None:
        target = _write(tmp_path / "dotfiles/creds.json", "old")
        real = tmp_path / "real/.credentials.json"
        real.parent.mkdir()
        real.symlink_to(target)
        link = tmp_path / "home/.claude/.credentials.json"
        link.parent.mkdir(parents=True)
        link.write_text("new")
        assert sync_credentials(tmp_path / "home", real) is not None
        assert real.is_symlink()
        assert target.read_text() == "new"

    def test_deleted_link_does_nothing(self, tmp_path: Path) -> None:
        real, link = self._setup(tmp_path)
        link.unlink()
        assert sync_credentials(tmp_path / "home", real) is None
        assert real.read_text() == "old"


class TestCleanEnv:
    def test_drops_claude_and_anthropic_vars_and_sets_home(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        monkeypatch.setenv("CLAUDECODE", "1")
        monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/x")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk")
        monkeypatch.setenv("PATH", "/usr/bin")
        env = clean_env(tmp_path)
        assert env["HOME"] == str(tmp_path)
        assert env["PATH"] == "/usr/bin"
        assert not any(k.startswith(("CLAUDE", "ANTHROPIC_")) for k in env)


class TestParseTurn:
    def test_extracts_fields(self) -> None:
        stdout = json.dumps(
            {
                "result": "5432.",
                "session_id": "s1",
                "is_error": False,
                "duration_ms": 900,
                "num_turns": 1,
                "usage": {"output_tokens": 12},
            }
        )
        assert parse_turn("q", stdout) == {
            "prompt": "q",
            "result": "5432.",
            "session_id": "s1",
            "is_error": False,
            "output_tokens": 12,
            "duration_ms": 900,
            "num_turns": 1,
        }

    def test_garbage_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_turn("q", "not json")


class TestAttemptTimeout:
    def test_refreshed_token_synced_even_when_turn_times_out(
        self, repo: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        real = _write(tmp_path / "real/.credentials.json", "old")
        monkeypatch.setattr(run_module, "WORK_ROOT", tmp_path / "jobs")

        def fake_run(cmd: list[str], **kwargs: object) -> None:
            link = Path(str(kwargs["env"]["HOME"])) / ".claude/.credentials.json"  # type: ignore[index]
            link.unlink()
            link.write_text("refreshed")
            raise subprocess.TimeoutExpired(cmd, 1)

        monkeypatch.setattr(run_module.subprocess, "run", fake_run)
        [v] = load_variants(repo / "variants.json", ["baseline"], repo)
        job = Job(v, "p", ["q"], 1, tmp_path / "out.json")
        _, error, _ = run_module._attempt(job, real)
        assert error is not None and "TimeoutExpired" in error
        assert real.read_text() == "refreshed"
        assert not any((tmp_path / "jobs").iterdir())
