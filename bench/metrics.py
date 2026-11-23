"""Text metrics for answer style and a report over a bench results directory.

Usage:
    python -m bench.metrics bench/results/<label>
"""

from __future__ import annotations

import json
import re
import statistics
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path

_FENCE = re.compile(r"^[ \t]*(```|~~~).*?(?:^[ \t]*\1[ \t]*$|\Z)", re.S | re.M)
_INLINE = re.compile(r"`[^`\n]+`")
_BULLET = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")
_HEADER = re.compile(r"^\s{0,3}#{1,6}\s")
_BOLD = re.compile(r"\*\*[^*\n]+\*\*")
_DASH_SUBSTITUTE = re.compile(r"(?<=\S) [-–] (?=\S)")
_WORD = re.compile(r"[а-яёa-z]+")
_ABBREVIATIONS = frozenset(
    [
        "т.",
        "д.",
        "п.",
        "е.",
        "к.",
        "др.",
        "пр.",
        "см.",
        "напр.",
        "т.е.",
        "т.д.",
        "т.п.",
        "т.к.",
        "e.g.",
        "i.e.",
        "etc.",
        "vs.",
    ]
)

_OPENERS = [
    r"(отличный|хороший|интересный|классный|правильный|резонный) вопрос",
    r"(great|good|excellent|interesting) question",
    r"(конечно|разумеется)\b",
    r"(sure|certainly|of course|absolutely)\b",
    r"давай(те)? (разбер|посмотр|начн|пройд)",
    r"(let me|let's|let us) ",
    r"(понял|понятно|ясно|окей|ok|okay)[,!.]",
    r"(привет|здравствуй|hi|hey|hello)\b",
    r"(ты|вы) (спрашиваешь|спрашиваете|хочешь узнать|хотите узнать)",
    r"(you're|you are) asking",
]

_CLOSERS = [
    r"если (хочешь|хотите|нужно|надо|интересно|понадобится)[^.?!]{0,80}"
    r"(могу|скажи|скажите|напиши|напишите|покажу|распишу|помогу|подскажу|дай знать|дайте знать"
    r"|сделаю|набросаю)",
    r"\bмогу (ещё|также|дальше|помочь|показать|расписать|подсказать|набросать|написать|сделать"
    r"|разобрать|объяснить)",
    r"(хочешь|хотите),? (я )?(покажу|распишу|сделаю|набросаю|напишу|разберу|объясню|помогу)",
    r"\bнадеюсь\b",
    r"дай(те)? знать",
    r"обращайся|обращайтесь",
    r"\bудачи\b",
    r"let me know",
    r"hope (this|that|it) helps",
    r"feel free",
    r"if you('d| would)? (want|like|need)",
    r"want me to",
    r"would you like",
    r"happy to help",
    r"good luck",
    r"i can also",
    r"shall i\b",
]

_SUMMARY = re.compile(
    r"^(итого|в итоге|резюмируя|подводя итог|подытожим|итог|итоги|вывод|выводы|резюме"
    r"|tl;dr|tldr|in summary|to summarize|to sum up|summary|bottom line|in short)"
    r"(\s*[:,.!—–-]|\s*$)"
)

_SLOP = [
    ("важно отметить", r"важно отметить"),
    ("стоит отметить", r"стоит отметить"),
    ("следует отметить", r"следует отметить"),
    ("стоит учесть", r"стоит учесть"),
    ("стоит обратить внимание", r"стоит обратить внимание"),
    ("необходимо учитывать", r"необходимо учитывать"),
    ("важно понимать", r"важно понимать"),
    ("играет ключевую роль", r"играет ключевую роль"),
    ("в современном мире", r"в современном мире"),
    ("it's worth noting", r"it'?s worth noting|it is worth noting"),
    ("it's important to note", r"it'?s important to note|it is important to note"),
    ("delve", r"\bdelv(e|es|ing)\b"),
    ("не X, а Y", r"\bне [^,.;:!?\n]{1,40}, а\b"),
    ("not just X", r"\bnot (just|only|merely) "),
]

_MAT = [
    r"бля\w*",
    r"ху[йеёияю]\w*",
    r"пизд\w*",
    r"(за|у|до|на|вы|от|по|про|съ|из|раз|при|въ|о|не)?еба[лнтш]\w*",
    r"(за|у|до|на|вы|от|по|про|съ|из|раз|при|въ|о)?ёб\w*",
    r"на(ху|хер)\w*",
    r"херн\w*",
    r"сук[аи]",
    r"пздц",
    r"fuck\w*",
    r"shit\w*",
]
_SLANG = [
    r"чё",
    r"ща",
    r"щас",
    r"норм",
    r"кринж\w*",
    r"имхо",
    r"лол",
    r"хз",
    r"братан\w*",
    r"чувак\w*",
]
_MIMICRY = re.compile("|".join(f"(?:{p})" for p in _MAT + _SLANG))


def strip_code(text: str) -> str:
    """Remove fenced code blocks and replace inline code with a placeholder.

    Args:
        text: Markdown answer.

    Returns:
        Prose only. Inline code becomes ``CODE`` so it never reads as a lowercase start.
    """
    return _INLINE.sub("CODE", _FENCE.sub("", text))


def first_line(text: str) -> str:
    """Return the first non-empty line, stripped."""
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _normalize_line(line: str) -> str:
    line = line.replace("**", "").replace("__", "")
    return re.sub(r"^[\s#>*_-]+", "", line).lower()


def _prose_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", strip_code(text)) if p.strip()]


def count_em_dashes(text: str) -> int:
    """Count em dashes outside code."""
    return strip_code(text).count("—")


def count_dash_substitutes(text: str) -> int:
    """Count spaced hyphens and en dashes used as a dash in prose, ignoring list markers."""
    return sum(len(_DASH_SUBSTITUTE.findall(ln)) for ln in strip_code(text).splitlines())


def has_opener(text: str) -> bool:
    """Whether the first line is a filler opener instead of the answer."""
    line = _normalize_line(first_line(text))
    return any(re.match(p, line) for p in _OPENERS)


def has_closer(text: str) -> bool:
    """Whether the last prose paragraph offers more help or signs off."""
    paragraphs = _prose_paragraphs(text)
    if not paragraphs:
        return False
    last = paragraphs[-1].lower()
    return any(re.search(p, last) for p in _CLOSERS)


def has_summary(text: str) -> bool:
    """Whether any prose line after the first opens a recap section."""
    lines = [ln for ln in strip_code(text).splitlines() if ln.strip()]
    return any(_SUMMARY.match(_normalize_line(ln)) for ln in lines[1:])


def find_slop(text: str) -> list[str]:
    """Return slop phrase labels in order of appearance."""
    prose = strip_code(text).lower()
    hits: list[tuple[int, str]] = []
    for label, pattern in _SLOP:
        hits.extend((m.start(), label) for m in re.finditer(pattern, prose))
    return [label for _, label in sorted(hits)]


def find_mimicry(text: str) -> list[str]:
    """Return swear and slang words found in prose, in order."""
    words = _WORD.findall(strip_code(text).lower())
    return [w for w in words if _MIMICRY.fullmatch(w)]


def _sentences(line: str) -> list[str]:
    parts, start = [], 0
    for m in re.finditer(r"[.!?…]\s+", line):
        before = line[start : m.start() + 1].split()
        word = before[-1].lstrip("(«\"'").lower() if before else ""
        if m.group()[0] == "." and word in _ABBREVIATIONS:
            continue
        parts.append(line[start : m.start() + 1])
        start = m.end()
    parts.append(line[start:])
    return parts


def count_lowercase_starts(text: str) -> int:
    """Count prose sentences starting with a lowercase Cyrillic letter.

    Lists, headers and tables are skipped. Latin starts are skipped too: they are almost
    always identifiers like ``arq`` or ``xid``, not a mimicked lowercase register.
    """
    total = 0
    for line in strip_code(text).splitlines():
        if not line.strip() or _BULLET.match(line) or _HEADER.match(line):
            continue
        if line.lstrip().startswith("|"):
            continue
        for sentence in _sentences(line.strip()):
            sentence = sentence.lstrip('*_"«(>')
            if re.match(r"[а-яё]", sentence):
                total += 1
    return total


def count_questions(text: str) -> int:
    """Count question marks in prose."""
    return strip_code(text).count("?")


def count_structure(text: str) -> dict[str, int]:
    """Count markdown headers, list items and bold spans in prose."""
    lines = strip_code(text).splitlines()
    return {
        "headers": sum(1 for ln in lines if _HEADER.match(ln)),
        "bullets": sum(1 for ln in lines if _BULLET.match(ln)),
        "bold": sum(len(_BOLD.findall(ln)) for ln in lines),
    }


@dataclass(frozen=True)
class AnswerMetrics:
    """All metrics for one answer."""

    chars: int
    output_tokens: int | None
    first_line_chars: int
    em_dashes: int
    dash_substitutes: int
    opener: bool
    closer: bool
    summary: bool
    questions: int
    lowercase_starts: int
    slop: list[str] = field(default_factory=list)
    mimicry: list[str] = field(default_factory=list)
    headers: int = 0
    bullets: int = 0
    bold: int = 0


def measure(text: str, output_tokens: int | None = None) -> AnswerMetrics:
    """Compute every metric for one answer."""
    return AnswerMetrics(
        chars=len(text.strip()),
        output_tokens=output_tokens,
        first_line_chars=len(first_line(text)),
        em_dashes=count_em_dashes(text),
        dash_substitutes=count_dash_substitutes(text),
        opener=has_opener(text),
        closer=has_closer(text),
        summary=has_summary(text),
        questions=count_questions(text),
        lowercase_starts=count_lowercase_starts(text),
        slop=find_slop(text),
        mimicry=find_mimicry(text),
        **count_structure(text),
    )


@dataclass(frozen=True)
class Record:
    """One measured answer from a results file."""

    variant: str
    prompt_id: str
    run: int
    prompt: str
    answer: str
    error: bool
    metrics: AnswerMetrics


def load_records(results_dir: Path) -> list[Record]:
    """Load every raw result under ``results_dir/raw`` and measure its last turn."""
    records = []
    for path in sorted((results_dir / "raw").glob("*/*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        turns = data.get("turns") or []
        last = turns[-1] if turns else {}
        answer = last.get("result") or ""
        records.append(
            Record(
                variant=data["variant"],
                prompt_id=data["prompt_id"],
                run=data["run"],
                prompt=last.get("prompt", ""),
                answer=answer,
                error=bool(data.get("error")) or not answer,
                metrics=measure(answer, last.get("output_tokens")),
            )
        )
    return records


def _mean(values: Sequence[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _variant_order(records: list[Record]) -> list[str]:
    return list(dict.fromkeys(r.variant for r in records))


def _summary_table(records: list[Record]) -> list[str]:
    head = [
        "| variant | n | err | chars | out tok | 1st line | — | ` - ` | opener | closer"
        " | summary | mimicry | slop | ? max | lowercase | hdr | bullets | bold |",
        "|" + "---|" * 18,
    ]
    rows = []
    for variant in _variant_order(records):
        rs = [r for r in records if r.variant == variant and not r.error]
        errors = sum(1 for r in records if r.variant == variant and r.error)
        ms = [r.metrics for r in rs]
        tokens = [m.output_tokens for m in ms if m.output_tokens is not None]
        rows.append(
            f"| {variant} | {len(rs)} | {errors} | {_mean([m.chars for m in ms]):.0f}"
            f" | {_mean(tokens):.0f} | {_mean([m.first_line_chars for m in ms]):.0f}"
            f" | {sum(m.em_dashes for m in ms)} | {sum(m.dash_substitutes for m in ms)}"
            f" | {sum(m.opener for m in ms)} | {sum(m.closer for m in ms)}"
            f" | {sum(m.summary for m in ms)} | {sum(len(m.mimicry) for m in ms)}"
            f" | {sum(len(m.slop) for m in ms)} | {max((m.questions for m in ms), default=0)}"
            f" | {sum(m.lowercase_starts for m in ms)} | {_mean([m.headers for m in ms]):.1f}"
            f" | {_mean([m.bullets for m in ms]):.1f} | {_mean([m.bold for m in ms]):.1f} |"
        )
    return head + rows


def _per_prompt_table(records: list[Record]) -> list[str]:
    variants = _variant_order(records)
    prompts = list(dict.fromkeys(r.prompt_id for r in records))
    lines = [
        "| prompt | " + " | ".join(variants) + " |",
        "|---|" + "---|" * len(variants),
    ]
    for pid in prompts:
        cells = []
        for v in variants:
            chars = [
                r.metrics.chars
                for r in records
                if r.prompt_id == pid and r.variant == v and not r.error
            ]
            cells.append(f"{_mean(chars):.0f}" if chars else "-")
        lines.append(f"| {pid} | " + " | ".join(cells) + " |")
    return lines


def _flags(m: AnswerMetrics) -> list[str]:
    flags = []
    if m.opener:
        flags.append("opener")
    if m.closer:
        flags.append("closer")
    if m.summary:
        flags.append("summary")
    if m.em_dashes:
        flags.append(f"em-dash×{m.em_dashes}")
    if m.dash_substitutes:
        flags.append(f"dash-sub×{m.dash_substitutes}")
    if m.questions > 1:
        flags.append(f"questions×{m.questions}")
    if m.mimicry:
        flags.append("mimicry: " + ", ".join(m.mimicry))
    if m.slop:
        flags.append("slop: " + ", ".join(m.slop))
    if m.lowercase_starts:
        flags.append(f"lowercase×{m.lowercase_starts}")
    return flags


def build_report(records: list[Record]) -> str:
    """Render the metrics report as markdown."""
    out = ["# Bench report", "", "Means per answer; counts are totals over answers.", ""]
    out += _summary_table(records)
    out += ["", "## Mean chars per prompt", ""]
    out += _per_prompt_table(records)
    out += ["", "## Flagged answers", ""]
    for r in records:
        if r.error:
            out.append(f"- `{r.variant}/{r.prompt_id}/r{r.run}`: ERROR or empty answer")
            continue
        flags = _flags(r.metrics)
        if flags:
            out.append(f"- `{r.variant}/{r.prompt_id}/r{r.run}`: " + "; ".join(flags))
    return "\n".join(out) + "\n"


def build_review(records: list[Record]) -> str:
    """Render run 1 of every variant side by side per prompt, for reading by eye."""
    out = ["# Answers for review", ""]
    for pid in dict.fromkeys(r.prompt_id for r in records):
        first = [r for r in records if r.prompt_id == pid and r.run == 1]
        if not first:
            continue
        out += [f"## {pid}", "", "> " + first[0].prompt.replace("\n", "\n> "), ""]
        for r in first:
            out += [
                f"### {r.variant} ({r.metrics.chars} chars)",
                "",
                r.answer.strip() or "_(empty)_",
                "",
            ]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    """Write report.md, review.md and metrics.json into the results directory."""
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    results_dir = Path(argv[1])
    records = load_records(results_dir)
    if not records:
        print(f"no results under {results_dir / 'raw'}", file=sys.stderr)
        return 1
    (results_dir / "report.md").write_text(build_report(records), encoding="utf-8")
    (results_dir / "review.md").write_text(build_review(records), encoding="utf-8")
    dump = [
        {"variant": r.variant, "prompt_id": r.prompt_id, "run": r.run, **asdict(r.metrics)}
        for r in records
    ]
    (results_dir / "metrics.json").write_text(
        json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(build_report(records))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
