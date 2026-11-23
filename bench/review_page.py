"""Build a local HTML page for rating answers as fine or cringe.

Usage:
    python -m bench.review_page OUT.html RESULTS_DIR:VARIANT:RUNS [...] [--before DIR:VARIANT]

Example:
    python -m bench.review_page /tmp/rate.html bench/results/v3:terse:1,4 \\
        bench/results/v2:claudeai-prefs:1 --before bench/results/v3:baseline

Ratings live in the browser's localStorage; the page exports them as JSON.
"""

from __future__ import annotations

import argparse
import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _last_answer(path: Path) -> tuple[str, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    turns = data.get("turns") or []
    if not turns:
        return "", ""
    return turns[-1].get("prompt", ""), turns[-1].get("result", "")


def collect(
    sources: list[tuple[Path, str, list[int]]],
    prompts: list[dict[str, Any]],
    before: tuple[Path, str] | None,
) -> list[dict[str, Any]]:
    """Gather the answers to rate, in prompt order.

    Args:
        sources: ``(results_dir, variant, runs)`` triples.
        prompts: Bench prompts (id, type, turns).
        before: Optional ``(results_dir, variant)`` shown as a collapsed reference (run 1).

    Returns:
        One item per existing answer file.
    """
    items = []
    for prompt in prompts:
        pid = prompt["id"]
        ref = ""
        if before:
            ref_path = before[0] / "raw" / before[1] / f"{pid}-r1.json"
            if ref_path.is_file():
                ref = _last_answer(ref_path)[1]
        for results_dir, variant, runs in sources:
            for run in runs:
                path = results_dir / "raw" / variant / f"{pid}-r{run}.json"
                if not path.is_file():
                    continue
                last_prompt, answer = _last_answer(path)
                items.append(
                    {
                        "key": f"{variant}/{pid}/r{run}",
                        "variant": variant,
                        "prompt_id": pid,
                        "type": prompt.get("type", ""),
                        "run": run,
                        "turns": prompt["turns"],
                        "prompt": last_prompt,
                        "answer": answer,
                        "before": ref,
                    }
                )
    return items


def embed_json(data: Any) -> str:
    """Serialize for a <script type="application/json"> block without breaking out of it."""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def render(items: list[dict[str, Any]], title: str) -> str:
    """Return the full HTML page."""
    page_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    return (
        _TEMPLATE.replace("__TITLE__", html.escape(title))
        .replace("__PAGE_ID__", page_id)
        .replace("__DATA__", embed_json(items))
    )


def _parse_source(raw: str) -> tuple[Path, str, list[int]]:
    directory, variant, runs = raw.rsplit(":", 2)
    return Path(directory), variant, [int(r) for r in runs.split(",")]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Build a rating page for bench answers.")
    parser.add_argument("out", type=Path)
    parser.add_argument("sources", nargs="+", help="RESULTS_DIR:VARIANT:RUN[,RUN...]")
    parser.add_argument("--before", help="RESULTS_DIR:VARIANT shown as reference")
    parser.add_argument("--title", default="Кринж или норм")
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parent.parent
    prompts = json.loads((repo / "bench" / "prompts.json").read_text(encoding="utf-8"))
    before = None
    if args.before:
        directory, variant = args.before.rsplit(":", 1)
        before = (Path(directory), variant)
    items = collect([_parse_source(s) for s in args.sources], prompts, before)
    args.out.write_text(render(items, args.title), encoding="utf-8")
    print(f"{len(items)} answers -> {args.out}")
    return 0


_TEMPLATE = r"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js"></script>
<style>
:root {
  --bg: #f6f5f2; --card: #ffffff; --text: #1d1d1b; --muted: #6b6a66; --line: #e2e0da;
  --ok: #2f7d4f; --ok-bg: #e5f3ea; --bad: #b03a2e; --bad-bg: #f8e4e1; --code: #f1efe9;
  --accent: #3b5bdb;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --bg: #161615; --card: #1f1f1d; --text: #e8e6e1; --muted: #9a978f; --line: #33322f;
    --ok: #6cc28e; --ok-bg: #1d3326; --bad: #ec8577; --bad-bg: #3a2220; --code: #2a2926;
    --accent: #8ea4ff;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font: 16px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif; }
header { position: sticky; top: 0; z-index: 5; background: var(--bg);
  border-bottom: 1px solid var(--line); padding: 12px 16px; }
.bar { max-width: 860px; margin: 0 auto; display: flex; gap: 12px; align-items: center;
  flex-wrap: wrap; }
.bar h1 { font-size: 17px; margin: 0 auto 0 0; }
.progress { color: var(--muted); font-size: 14px; }
.filter { display: flex; gap: 6px; }
button { font: inherit; font-size: 14px; border: 1px solid var(--line); background: var(--card);
  color: var(--text); border-radius: 8px; padding: 6px 12px; cursor: pointer; }
button:hover { border-color: var(--muted); }
button.primary { background: var(--accent); border-color: var(--accent); color: #fff; }
button.active { border-color: var(--text); }
main { max-width: 860px; margin: 0 auto; padding: 16px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  margin: 0 0 20px; overflow: hidden; }
.card.ok { border-color: var(--ok); }
.card.bad { border-color: var(--bad); }
.meta { display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 16px 0; font-size: 13px;
  color: var(--muted); }
.tag { border: 1px solid var(--line); border-radius: 999px; padding: 1px 8px; }
.prompt { margin: 10px 16px 0; padding: 10px 12px; background: var(--code); border-radius: 8px;
  white-space: pre-wrap; font-size: 14px; }
.prompt + .prompt { margin-top: 6px; }
.answer { padding: 4px 16px 0; overflow-wrap: anywhere; }
.answer.clamped { max-height: 560px; overflow: hidden; position: relative; }
.answer.clamped::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0;
  height: 80px; background: linear-gradient(transparent, var(--card)); }
.more { margin: 6px 16px 0; }
.answer pre, .ref pre { background: var(--code); padding: 10px 12px; border-radius: 8px;
  overflow-x: auto; font-size: 13px; }
.answer code, .ref code { background: var(--code); padding: 1px 4px; border-radius: 4px;
  font-size: 0.9em; }
.answer pre code, .ref pre code { background: none; padding: 0; }
.answer table, .ref table { border-collapse: collapse; display: block; overflow-x: auto; }
.answer td, .answer th, .ref td, .ref th { border: 1px solid var(--line); padding: 4px 8px; }
details.before { margin: 10px 16px 0; border-top: 1px dashed var(--line); padding-top: 8px; }
details.before summary { cursor: pointer; color: var(--muted); font-size: 14px; }
.ref { font-size: 14px; opacity: 0.85; }
.rate { display: flex; gap: 8px; align-items: flex-start; flex-wrap: wrap; padding: 14px 16px 16px; }
.rate button.ok.on { background: var(--ok-bg); border-color: var(--ok); color: var(--ok); }
.rate button.bad.on { background: var(--bad-bg); border-color: var(--bad); color: var(--bad); }
.rate textarea { flex: 1 1 240px; min-height: 38px; font: inherit; font-size: 14px;
  background: var(--bg); color: var(--text); border: 1px solid var(--line); border-radius: 8px;
  padding: 6px 10px; resize: vertical; }
.toast { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%);
  background: var(--text); color: var(--bg); padding: 8px 14px; border-radius: 8px;
  font-size: 14px; opacity: 0; transition: opacity .2s; pointer-events: none; }
.toast.show { opacity: 1; }
</style>
</head>
<body>
<header><div class="bar">
  <h1>__TITLE__</h1>
  <span class="progress" id="progress"></span>
  <span class="filter">
    <button data-f="all" class="active">все</button>
    <button data-f="todo">без оценки</button>
    <button data-f="bad">кринж</button>
  </span>
  <button id="copy">Скопировать</button>
  <button id="save" class="primary">Скачать JSON</button>
</div></header>
<main id="list"></main>
<div class="toast" id="toast"></div>
<script type="application/json" id="data">__DATA__</script>
<script>
const items = JSON.parse(document.getElementById("data").textContent);
const storeKey = "rate-__PAGE_ID__";
let state = {};
try { state = JSON.parse(localStorage.getItem(storeKey) || "{}"); } catch (e) { state = {}; }
const persist = () => { try { localStorage.setItem(storeKey, JSON.stringify(state)); } catch (e) {} };

const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
if (window.marked) {
  // Raw HTML inside an answer is shown as text, never rendered or executed.
  marked.use({ renderer: { html: (token) => escapeHtml(typeof token === "string" ? token : token.text) } });
}
const md = (text) => {
  if (window.marked) return marked.parse(text || "");
  const pre = document.createElement("pre");
  pre.textContent = text || "";
  return pre.outerHTML;
};

const list = document.getElementById("list");
let filter = "all";

function card(item) {
  const s = state[item.key] || {};
  const el = document.createElement("section");
  el.className = "card" + (s.verdict ? " " + s.verdict : "");
  el.dataset.key = item.key;
  const prompts = item.turns.map((t) => `<div class="prompt"></div>`).join("");
  el.innerHTML = `
    <div class="meta"><span class="tag"></span><span class="tag"></span><span class="tag"></span></div>
    ${prompts}
    <div class="answer"></div>
    <button class="more" hidden>развернуть</button>
    ${item.before ? `<details class="before"><summary>как было без правил</summary><div class="ref"></div></details>` : ""}
    <div class="rate">
      <button class="ok">норм</button>
      <button class="bad">кринж</button>
      <textarea placeholder="что не так (необязательно)"></textarea>
    </div>`;
  const tags = el.querySelectorAll(".tag");
  tags[0].textContent = item.type;
  tags[1].textContent = item.variant;
  tags[2].textContent = "прогон " + item.run;
  el.querySelectorAll(".prompt").forEach((p, i) => { p.textContent = item.turns[i]; });
  const answer = el.querySelector(".answer");
  answer.innerHTML = md(item.answer);
  if (item.answer.length > 2500) {
    answer.classList.add("clamped");
    const more = el.querySelector(".more");
    more.hidden = false;
    more.onclick = () => {
      const on = answer.classList.toggle("clamped");
      more.textContent = on ? "развернуть" : "свернуть";
    };
  }
  const ref = el.querySelector(".ref");
  if (ref) ref.innerHTML = md(item.before);
  const ok = el.querySelector(".rate .ok");
  const bad = el.querySelector(".rate .bad");
  const note = el.querySelector("textarea");
  note.value = s.comment || "";
  const paint = () => {
    const v = (state[item.key] || {}).verdict;
    ok.classList.toggle("on", v === "ok");
    bad.classList.toggle("on", v === "bad");
    el.className = "card" + (v ? " " + v : "");
  };
  const set = (v) => {
    const cur = state[item.key] || {};
    state[item.key] = { ...cur, verdict: cur.verdict === v ? undefined : v };
    persist(); paint(); update();
  };
  ok.onclick = () => set("ok");
  bad.onclick = () => set("bad");
  note.oninput = () => { state[item.key] = { ...(state[item.key] || {}), comment: note.value }; persist(); };
  paint();
  return el;
}

items.forEach((it) => list.appendChild(card(it)));

function update() {
  const rated = items.filter((it) => (state[it.key] || {}).verdict).length;
  const bad = items.filter((it) => (state[it.key] || {}).verdict === "bad").length;
  document.getElementById("progress").textContent = `оценено ${rated} из ${items.length}, кринж ${bad}`;
  list.querySelectorAll(".card").forEach((el) => {
    const v = (state[el.dataset.key] || {}).verdict;
    el.hidden = (filter === "todo" && v) || (filter === "bad" && v !== "bad");
  });
}
document.querySelectorAll(".filter button").forEach((b) => {
  b.onclick = () => {
    filter = b.dataset.f;
    document.querySelectorAll(".filter button").forEach((x) => x.classList.toggle("active", x === b));
    update();
  };
});
update();

function exportData() {
  return JSON.stringify({
    page: "__PAGE_ID__",
    exported: new Date().toISOString(),
    ratings: items.map((it) => ({
      key: it.key, variant: it.variant, prompt_id: it.prompt_id, run: it.run,
      verdict: (state[it.key] || {}).verdict || null,
      comment: (state[it.key] || {}).comment || "",
    })),
  }, null, 1);
}
const toast = (msg) => {
  const t = document.getElementById("toast");
  t.textContent = msg; t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 1600);
};
document.getElementById("save").onclick = () => {
  const blob = new Blob([exportData()], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "cringe-ratings-__PAGE_ID__.json";
  a.click();
  toast("Сохранено в загрузки");
};
document.getElementById("copy").onclick = async () => {
  try { await navigator.clipboard.writeText(exportData()); toast("Скопировано"); }
  catch (e) { toast("Не вышло, жми «Скачать JSON»"); }
};
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
