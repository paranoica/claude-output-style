import json
import re
from pathlib import Path

from bench.review_page import collect, embed_json, render


def _result(root: Path, variant: str, pid: str, run: int, answer: str) -> None:
    path = root / "raw" / variant / f"{pid}-r{run}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"turns": [{"prompt": "q", "result": answer}]}), encoding="utf-8")


PROMPTS = [
    {"id": "01", "type": "факт", "turns": ["q1"]},
    {"id": "02", "type": "дебаг", "turns": ["q2a", "q2b"]},
]


class TestCollect:
    def test_prompt_order_then_sources_then_runs(self, tmp_path: Path) -> None:
        for pid in ("01", "02"):
            for run in (1, 4):
                _result(tmp_path, "terse", pid, run, f"{pid}-{run}")
        _result(tmp_path, "prefs", "01", 1, "p")
        items = collect([(tmp_path, "terse", [1, 4]), (tmp_path, "prefs", [1])], PROMPTS, None)
        assert [i["key"] for i in items] == [
            "terse/01/r1",
            "terse/01/r4",
            "prefs/01/r1",
            "terse/02/r1",
            "terse/02/r4",
        ]

    def test_missing_files_skipped(self, tmp_path: Path) -> None:
        _result(tmp_path, "terse", "02", 1, "x")
        items = collect([(tmp_path, "terse", [1, 2])], PROMPTS, None)
        assert [i["key"] for i in items] == ["terse/02/r1"]

    def test_before_reference_from_run_one(self, tmp_path: Path) -> None:
        _result(tmp_path, "terse", "01", 1, "after")
        _result(tmp_path, "baseline", "01", 1, "before")
        [item] = collect([(tmp_path, "terse", [1])], PROMPTS, (tmp_path, "baseline"))
        assert item["before"] == "before"
        assert item["answer"] == "after"

    def test_multi_turn_keeps_all_turns(self, tmp_path: Path) -> None:
        _result(tmp_path, "terse", "02", 1, "x")
        [item] = collect([(tmp_path, "terse", [1])], PROMPTS, None)
        assert item["turns"] == ["q2a", "q2b"]


class TestEmbedding:
    def test_script_close_tag_cannot_break_out(self) -> None:
        payload = [{"answer": "</script><script>alert(1)</script>"}]
        embedded = embed_json(payload)
        assert "</script" not in embedded.lower()
        assert json.loads(embedded) == payload

    def test_rendered_page_round_trips_data(self, tmp_path: Path) -> None:
        items = [{"key": "k", "answer": "a </script> b <!-- c", "turns": ["q"]}]
        page = render(items, "T <b>")
        block = re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S)
        assert block is not None
        assert json.loads(block.group(1)) == items
        assert "<title>T &lt;b&gt;</title>" in page

    def test_no_placeholders_left(self) -> None:
        assert "__" not in "".join(re.findall(r"__[A-Z_]+__", render([], "t")))
