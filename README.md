# claude-output-style

A short rule set that makes Claude's answers direct and compact: the answer comes first, with no intros, no recaps and no "let me know if you want more". The voice stays neutral and never imitates the user's slang. The rules are in Russian, but they apply to English answers too.

Works in Claude Code (via `~/.claude/CLAUDE.md`) and on claude.ai (via the Instructions field).

## Before and after

> what should I use for background jobs: celery, rq or arq? ~1000 jobs a day

**Before:** a `## Why arq` heading, a bullet list with every item bolded, em dashes, and a closing "Show me what the jobs do and I can be more specific."

**After:** "arq if the jobs are async, rq if they are sync. Celery is overkill for 1000 jobs a day: …"

More pairs are in [examples.md](examples.md).

## Install

Claude Code:

```bash
git clone https://github.com/paranoica/claude-output-style.git
cd claude-output-style
./install.sh
```

The script appends the rules to `~/.claude/CLAUDE.md` between marker comments, so your existing text is untouched and re-running it only updates the block. It backs up every file it changes to `<file>.bak-<timestamp>`. Restart running sessions to pick up the rules.

If an output style is active, the script unsets it, because a style overrides these rules. Pass `--keep-style` to leave it alone.

To remove the rules: `./install.sh --uninstall`.

claude.ai: paste [claude-ai-preferences.md](claude-ai-preferences.md) into Settings → Your Claude → Instructions.

## Does it work?

Tested on 10 prompts of different kinds (a quick fact, code how-to, debugging from a traceback, a personal question, and so on), 6 runs each, through `claude -p`. The table compares the rules with plain Claude Code.

| | Plain Claude Code | With the rules |
|---|---|---|
| Average answer length | 2586 chars | 1372 chars (−47%) |
| Output tokens | 1533 | 920 (−40%) |
| Em dashes | 43 in 30 answers | 1 in 60 |
| "Want me to…" endings | 8 in 30 | 0 |
| Copying the user's slang | n/a | 0 |

On a manual "is this cringe?" check of 30 answers, all 30 passed.

## Files

| File | What it is |
|---|---|
| `CLAUDE.md` | the rules block for Claude Code |
| `claude-ai-preferences.md` | a shorter version for claude.ai |
| `output-styles/plain.md` | the same rules as a Claude Code output style (`./install.sh --with-style`) |
| `install.sh` | install, update, uninstall |
| `bench/` | the test harness (below) |

## Test harness

```bash
python3 -m bench.run --variants baseline,claudemd --runs 3 --label my-run
python3 -m bench.metrics bench/results/my-run
```

Each run uses a throwaway HOME, so your own config, plugins and MCP servers don't leak into the answers. Prompts live in `bench/prompts.json` and variants in `bench/variants.json`. `metrics` writes `report.md` with counts per variant and `review.md` with the answers side by side. `python3 -m bench.review_page` builds a local HTML page for rating answers by hand.

Tests: `uv run --no-project --with pytest pytest`.
