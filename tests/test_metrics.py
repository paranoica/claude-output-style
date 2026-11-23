from bench.metrics import (
    count_dash_substitutes,
    count_em_dashes,
    count_lowercase_starts,
    count_questions,
    count_structure,
    find_mimicry,
    find_slop,
    first_line,
    has_closer,
    has_opener,
    has_summary,
    strip_code,
)


class TestStripCode:
    def test_removes_fenced_block_with_contents(self) -> None:
        text = "До\n```bash\necho — - x\n```\nПосле"
        assert "echo" not in strip_code(text)
        assert "До" in strip_code(text)
        assert "После" in strip_code(text)

    def test_replaces_inline_code_with_placeholder(self) -> None:
        assert strip_code("Запусти `ls -la` сейчас") == "Запусти CODE сейчас"

    def test_unclosed_fence_drops_rest(self) -> None:
        assert strip_code("Текст\n```\ncode — here").strip() == "Текст"

    def test_empty(self) -> None:
        assert strip_code("") == ""


class TestFirstLine:
    def test_skips_leading_blank_lines(self) -> None:
        assert first_line("\n\n  Порт 5432.\nДальше") == "Порт 5432."

    def test_empty_text(self) -> None:
        assert first_line("") == ""
        assert first_line("\n  \n") == ""


class TestDashes:
    def test_counts_em_dash_in_prose(self) -> None:
        assert count_em_dashes("Москва — столица, а Питер — нет.") == 2

    def test_ignores_em_dash_in_code(self) -> None:
        assert count_em_dashes("Текст.\n```\na — b\n```\n`x — y`") == 0

    def test_en_dash_in_number_range_is_not_em_dash(self) -> None:
        assert count_em_dashes("Страницы 10–20.") == 0

    def test_spaced_hyphen_mid_line_counts(self) -> None:
        assert count_dash_substitutes("Москва - столица.") == 1

    def test_spaced_en_dash_counts_as_substitute(self) -> None:
        assert count_dash_substitutes("Москва – столица.") == 1

    def test_bullet_marker_is_not_substitute(self) -> None:
        assert count_dash_substitutes("- первый\n  - вложенный\n- второй") == 0

    def test_hyphenated_word_is_not_substitute(self) -> None:
        assert count_dash_substitutes("что-то и кто-нибудь") == 0

    def test_hyphen_in_code_ignored(self) -> None:
        assert count_dash_substitutes("Флаг `a - b`.\n```\nx - y\n```") == 0


class TestOpener:
    def test_flattery_opener(self) -> None:
        assert has_opener("Отличный вопрос! Порт 5432.")

    def test_english_opener(self) -> None:
        assert has_opener("Great question. Use rebase when...")

    def test_lets_break_down(self) -> None:
        assert has_opener("Давай разберёмся по шагам.\n1. ...")

    def test_bold_wrapped_opener(self) -> None:
        assert has_opener("**Конечно!** Вот команда.")

    def test_direct_answer_is_not_opener(self) -> None:
        assert not has_opener("По умолчанию 5432.")

    def test_opener_word_mid_line_is_not_opener(self) -> None:
        assert not has_opener("Порт 5432, конечно.")

    def test_opener_only_checked_on_first_line(self) -> None:
        assert not has_opener("Порт 5432.\nОтличный вопрос, кстати.")

    def test_empty(self) -> None:
        assert not has_opener("")


class TestCloser:
    def test_offer_in_last_paragraph(self) -> None:
        assert has_closer("Порт 5432.\n\nЕсли хочешь, могу показать конфиг.")

    def test_want_me_to(self) -> None:
        assert has_closer("Use merge.\n\nWant me to show an example?")

    def test_hope_helps(self) -> None:
        assert has_closer("Done.\n\nHope this helps!")

    def test_offer_in_middle_is_not_closer(self) -> None:
        text = "Могу показать конфиг ниже.\n\nКонфиг лежит в /etc/postgresql."
        assert not has_closer(text)

    def test_conditional_instruction_is_not_closer(self) -> None:
        assert not has_closer("Готово.\n\nЕсли нужно ограничить вывод, добавь `-n 10`.")

    def test_offer_hidden_in_code_tail_is_not_closer(self) -> None:
        assert not has_closer("Пример:\n```\n# могу ещё показать\n```")

    def test_empty(self) -> None:
        assert not has_closer("")


class TestSummary:
    def test_itogo_line(self) -> None:
        assert has_summary("Шаги...\n\nИтого: используй rebase.")

    def test_bold_summary(self) -> None:
        assert has_summary("Текст\n\n**В итоге:** всё ок.")

    def test_summary_header(self) -> None:
        assert has_summary("## Шаги\n...\n## Итог\nВсё.")

    def test_english_tldr(self) -> None:
        assert has_summary("Long text.\n\nTL;DR: use merge.")

    def test_word_inside_sentence_not_summary(self) -> None:
        assert not has_summary("Функция возвращает итоговую сумму.")

    def test_verdict_on_first_line_is_answer_not_summary(self) -> None:
        assert not has_summary("Вывод: бери rq.\nПотому что сервер один.")

    def test_keyword_as_word_prefix_or_subject_is_not_summary(self) -> None:
        assert not has_summary("Шаги ниже.\nИтоговая таблица ниже.\nВывод команды:")

    def test_summary_inside_code_ignored(self) -> None:
        assert not has_summary("```\n# Итого\n```")


class TestSlop:
    def test_finds_phrases(self) -> None:
        hits = find_slop("Важно отметить, что это так. Также стоит учесть нюанс.")
        assert hits == ["важно отметить", "стоит учесть"]

    def test_not_x_but_y(self) -> None:
        assert find_slop("Это не баг, а фича.") == ["не X, а Y"]

    def test_ne_inside_word_is_not_contrast(self) -> None:
        assert find_slop("В тишине работы, а потом шум.") == []

    def test_clean_text(self) -> None:
        assert find_slop("Порт 5432. Меняется в postgresql.conf.") == []


class TestMimicry:
    def test_mat(self) -> None:
        assert find_mimicry("Да, это бля неприятно.") == ["бля"]

    def test_mat_inflected(self) -> None:
        assert find_mimicry("Заебался? Понимаю.") == ["заебался"]

    def test_slang(self) -> None:
        assert find_mimicry("Чё, норм работает?") == ["чё", "норм"]

    def test_lookalike_words_not_flagged(self) -> None:
        clean = "Колебался долго. Нормально, хуже не стало. Потребление упало. Ребалансировка."
        assert find_mimicry(clean) == []

    def test_mat_in_code_ignored(self) -> None:
        assert find_mimicry("```\necho бля\n```") == []


class TestLowercaseStarts:
    def test_counts_prose_sentences(self) -> None:
        assert count_lowercase_starts("короче так. дальше смотри. Это норм.") == 2

    def test_abbreviations_do_not_end_sentence(self) -> None:
        text = "Флаги -e, -f и т.п. проходят по ссылке. Т.е. всё так, и т.д. и т. д. дальше."
        assert count_lowercase_starts(text) == 0

    def test_lowercase_after_real_sentence_end_still_counted(self) -> None:
        assert count_lowercase_starts("Ок. и т.п. тоже.") == 1

    def test_list_items_ignored(self) -> None:
        assert count_lowercase_starts("Шаги:\n- сначала это\n1. потом то") == 0

    def test_inline_code_start_ignored(self) -> None:
        assert count_lowercase_starts("`ls` выводит файлы.") == 0

    def test_empty(self) -> None:
        assert count_lowercase_starts("") == 0


class TestQuestions:
    def test_counts_question_marks_in_prose(self) -> None:
        assert count_questions("Какой порт? А версия? Ладно.") == 2

    def test_ignores_code(self) -> None:
        assert count_questions("```\nre = r'a?b?'\n```\n`x?`") == 0


class TestStructure:
    def test_counts_headers_bullets_bold(self) -> None:
        text = "## Шаги\n- **один**\n- два\n1. три\n\n**Важно** тут"
        assert count_structure(text) == {"headers": 1, "bullets": 3, "bold": 2}

    def test_code_not_counted(self) -> None:
        assert count_structure("```\n# comment\n- item\n```") == {
            "headers": 0,
            "bullets": 0,
            "bold": 0,
        }
