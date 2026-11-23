# Bench report

Means per answer; counts are totals over answers.

| variant | n | err | chars | out tok | 1st line | — | ` - ` | opener | closer | summary | mimicry | slop | ? max | lowercase | hdr | bullets | bold |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 30 | 0 | 5323 | 3425 | 71 | 43 | 0 | 3 | 8 | 1 | 0 | 14 | 4 | 1 | 7.7 | 16.6 | 14.7 |
| claudeai-base | 30 | 0 | 5139 | 3368 | 68 | 115 | 0 | 2 | 5 | 3 | 0 | 22 | 3 | 0 | 6.9 | 16.1 | 17.2 |
| claudeai-prefs | 30 | 0 | 3276 | 2513 | 170 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 2.4 | 5.8 | 2.5 |
| claudemd | 30 | 0 | 3440 | 2241 | 191 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 2 | 2 | 2.4 | 8.3 | 4.1 |
| current | 30 | 0 | 3744 | 3096 | 99 | 1 | 0 | 3 | 4 | 0 | 2 | 5 | 2 | 0 | 2.9 | 7.8 | 2.7 |
| installed | 30 | 0 | 3965 | 2677 | 185 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 1 | 1 | 3.3 | 8.3 | 3.8 |

## Mean chars per prompt

| prompt | baseline | claudeai-base | claudeai-prefs | claudemd | current | installed |
|---|---|---|---|---|---|---|
| 01-fact | 124 | 135 | 116 | 110 | 30 | 99 |
| 02-howto | 2634 | 2003 | 1500 | 1486 | 1691 | 1693 |
| 03-concept | 5317 | 5041 | 2909 | 2848 | 3451 | 3200 |
| 04-choice | 2225 | 2269 | 1229 | 971 | 1503 | 1199 |
| 05-debug | 2208 | 2399 | 1643 | 1563 | 1716 | 1787 |
| 06-personal | 1941 | 2086 | 1425 | 1279 | 1603 | 1121 |
| 07-deep | 29961 | 28390 | 18203 | 20602 | 21641 | 24297 |
| 08-english | 2494 | 2789 | 1970 | 1914 | 1970 | 2283 |
| 09-multistep | 5304 | 5294 | 3203 | 3130 | 3318 | 3428 |
| 10-followup | 1024 | 986 | 558 | 493 | 522 | 547 |

## Flagged answers

- `baseline/02-howto/r1`: closer
- `baseline/03-concept/r1`: slop: не X, а Y
- `baseline/03-concept/r2`: summary; em-dash×2; slop: не X, а Y
- `baseline/03-concept/r3`: em-dash×4
- `baseline/04-choice/r1`: em-dash×4
- `baseline/04-choice/r3`: questions×3
- `baseline/06-personal/r1`: opener; closer; questions×2
- `baseline/06-personal/r2`: opener; closer; questions×2; slop: не X, а Y, не X, а Y
- `baseline/06-personal/r3`: opener; closer; em-dash×1; questions×4; slop: не X, а Y, не X, а Y, не X, а Y
- `baseline/07-deep/r1`: closer; em-dash×14; slop: не X, а Y, не X, а Y
- `baseline/07-deep/r2`: closer; em-dash×6; slop: не X, а Y
- `baseline/07-deep/r3`: closer; em-dash×12; slop: не X, а Y, не X, а Y, не X, а Y, не X, а Y; lowercase×1
- `baseline/09-multistep/r1`: closer
- `claudeai-base/03-concept/r1`: slop: не X, а Y, важно понимать
- `claudeai-base/03-concept/r2`: em-dash×1
- `claudeai-base/03-concept/r3`: summary; em-dash×7
- `claudeai-base/04-choice/r1`: summary; em-dash×1; slop: не X, а Y
- `claudeai-base/04-choice/r2`: em-dash×2
- `claudeai-base/04-choice/r3`: em-dash×1
- `claudeai-base/05-debug/r1`: em-dash×1
- `claudeai-base/06-personal/r1`: opener; closer; questions×3; slop: не X, а Y, не X, а Y, не X, а Y
- `claudeai-base/06-personal/r2`: closer; questions×2; slop: не X, а Y, не X, а Y
- `claudeai-base/06-personal/r3`: opener; closer; em-dash×9; slop: не X, а Y, не X, а Y, не X, а Y, не X, а Y
- `claudeai-base/07-deep/r1`: em-dash×18; slop: не X, а Y
- `claudeai-base/07-deep/r2`: closer; summary; em-dash×39; slop: не X, а Y, не X, а Y
- `claudeai-base/07-deep/r3`: closer; em-dash×35; slop: не X, а Y, не X, а Y, не X, а Y, не X, а Y, не X, а Y
- `claudeai-base/09-multistep/r1`: em-dash×1; slop: не X, а Y
- `claudeai-base/10-followup/r3`: slop: не X, а Y
- `claudemd/03-concept/r1`: slop: не X, а Y
- `claudemd/06-personal/r2`: slop: не X, а Y
- `claudemd/06-personal/r3`: questions×2
- `claudemd/07-deep/r1`: slop: не X, а Y, не X, а Y; lowercase×1
- `claudemd/07-deep/r2`: slop: не X, а Y
- `claudemd/07-deep/r3`: slop: не X, а Y, важно понимать; lowercase×1
- `current/03-concept/r3`: em-dash×1
- `current/05-debug/r1`: slop: не X, а Y
- `current/06-personal/r1`: opener; mimicry: норм
- `current/06-personal/r2`: opener; closer; slop: не X, а Y
- `current/06-personal/r3`: opener; closer; questions×2; mimicry: норм; slop: не X, а Y, не X, а Y
- `current/07-deep/r2`: closer
- `current/07-deep/r3`: closer; slop: не X, а Y
- `installed/07-deep/r1`: slop: не X, а Y
- `installed/07-deep/r2`: slop: не X, а Y, не X, а Y
- `installed/07-deep/r3`: slop: не X, а Y; lowercase×1
