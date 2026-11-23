# Bench report

Means per answer; counts are totals over answers.

| variant | n | err | chars | out tok | 1st line | — | ` - ` | opener | closer | summary | mimicry | slop | ? max | lowercase | hdr | bullets | bold |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 30 | 0 | 5323 | 3425 | 71 | 43 | 0 | 3 | 8 | 1 | 0 | 14 | 4 | 1 | 7.7 | 16.6 | 14.7 |
| claudemd | 60 | 0 | 3527 | 2501 | 194 | 0 | 0 | 0 | 0 | 0 | 0 | 8 | 2 | 3 | 2.6 | 8.2 | 3.7 |
| terse | 60 | 0 | 3442 | 3032 | 146 | 1 | 0 | 0 | 0 | 1 | 0 | 6 | 1 | 1 | 3.0 | 7.0 | 1.9 |

## Mean chars per prompt

| prompt | baseline | claudemd | terse |
|---|---|---|---|
| 01-fact | 124 | 102 | 97 |
| 02-howto | 2634 | 1522 | 1460 |
| 03-concept | 5317 | 2907 | 2444 |
| 04-choice | 2225 | 1002 | 1040 |
| 05-debug | 2208 | 1518 | 1445 |
| 06-personal | 1941 | 1207 | 1161 |
| 07-deep | 29961 | 21494 | 22067 |
| 08-english | 2494 | 1979 | 1438 |
| 09-multistep | 5304 | 2993 | 2738 |
| 10-followup | 1024 | 544 | 529 |

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
- `claudemd/03-concept/r1`: slop: не X, а Y
- `claudemd/06-personal/r2`: slop: не X, а Y
- `claudemd/06-personal/r3`: questions×2
- `claudemd/07-deep/r1`: slop: не X, а Y, не X, а Y; lowercase×1
- `claudemd/07-deep/r2`: slop: не X, а Y
- `claudemd/07-deep/r3`: slop: не X, а Y, важно понимать; lowercase×1
- `claudemd/07-deep/r4`: slop: не X, а Y
- `claudemd/07-deep/r6`: lowercase×1
- `terse/03-concept/r5`: slop: не X, а Y, не X, а Y
- `terse/04-choice/r3`: em-dash×1
- `terse/07-deep/r1`: slop: важно понимать
- `terse/07-deep/r2`: lowercase×1
- `terse/07-deep/r3`: summary
- `terse/07-deep/r4`: slop: не X, а Y
- `terse/07-deep/r5`: slop: не X, а Y
- `terse/07-deep/r6`: slop: не X, а Y
