# Bench report

Means per answer; counts are totals over answers.

| variant | n | err | chars | out tok | 1st line | — | ` - ` | opener | closer | summary | mimicry | slop | ? max | lowercase | hdr | bullets | bold |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 30 | 0 | 5323 | 3425 | 71 | 43 | 0 | 3 | 8 | 1 | 0 | 14 | 4 | 1 | 7.7 | 16.6 | 14.7 |
| both | 30 | 0 | 3845 | 2708 | 181 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 1 | 0 | 2.8 | 7.2 | 3.6 |
| claudemd | 30 | 0 | 3440 | 2241 | 191 | 0 | 0 | 0 | 0 | 0 | 0 | 7 | 2 | 2 | 2.4 | 8.3 | 4.1 |
| current | 30 | 0 | 3744 | 3096 | 99 | 1 | 0 | 3 | 4 | 0 | 2 | 5 | 2 | 0 | 2.9 | 7.8 | 2.7 |
| style | 30 | 0 | 3966 | 3142 | 210 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 2 | 0 | 3.1 | 7.6 | 2.6 |

## Mean chars per prompt

| prompt | baseline | both | claudemd | current | style |
|---|---|---|---|---|---|
| 01-fact | 124 | 100 | 110 | 30 | 113 |
| 02-howto | 2634 | 1532 | 1486 | 1691 | 1572 |
| 03-concept | 5317 | 2800 | 2848 | 3451 | 3153 |
| 04-choice | 2225 | 1023 | 971 | 1503 | 1300 |
| 05-debug | 2208 | 1621 | 1563 | 1716 | 1648 |
| 06-personal | 1941 | 1259 | 1279 | 1603 | 1212 |
| 07-deep | 29961 | 24553 | 20602 | 21641 | 24612 |
| 08-english | 2494 | 2081 | 1914 | 1970 | 2162 |
| 09-multistep | 5304 | 2942 | 3130 | 3318 | 3326 |
| 10-followup | 1024 | 535 | 493 | 522 | 559 |

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
- `both/05-debug/r3`: slop: не X, а Y
- `both/06-personal/r3`: slop: не X, а Y
- `both/07-deep/r1`: slop: не X, а Y
- `both/07-deep/r2`: slop: не X, а Y
- `both/07-deep/r3`: slop: не X, а Y, не X, а Y
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
- `style/06-personal/r1`: slop: стоит учесть
- `style/06-personal/r3`: questions×2
- `style/07-deep/r1`: slop: не X, а Y
- `style/07-deep/r2`: slop: не X, а Y, не X, а Y
