# Bench report

Means per answer; counts are totals over answers.

| variant | n | err | chars | out tok | 1st line | — | ` - ` | opener | closer | summary | mimicry | slop | ? max | lowercase | hdr | bullets | bold |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 30 | 0 | 5323 | 3425 | 71 | 43 | 0 | 3 | 8 | 1 | 0 | 14 | 4 | 1 | 7.7 | 16.6 | 14.7 |
| current | 30 | 0 | 3744 | 3096 | 99 | 1 | 0 | 3 | 4 | 0 | 2 | 5 | 2 | 0 | 2.9 | 7.8 | 2.7 |

## Mean chars per prompt

| prompt | baseline | current |
|---|---|---|
| 01-fact | 124 | 30 |
| 02-howto | 2634 | 1691 |
| 03-concept | 5317 | 3451 |
| 04-choice | 2225 | 1503 |
| 05-debug | 2208 | 1716 |
| 06-personal | 1941 | 1603 |
| 07-deep | 29961 | 21641 |
| 08-english | 2494 | 1970 |
| 09-multistep | 5304 | 3318 |
| 10-followup | 1024 | 522 |

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
- `current/03-concept/r3`: em-dash×1
- `current/05-debug/r1`: slop: не X, а Y
- `current/06-personal/r1`: opener; mimicry: норм
- `current/06-personal/r2`: opener; closer; slop: не X, а Y
- `current/06-personal/r3`: opener; closer; questions×2; mimicry: норм; slop: не X, а Y, не X, а Y
- `current/07-deep/r2`: closer
- `current/07-deep/r3`: closer; slop: не X, а Y
