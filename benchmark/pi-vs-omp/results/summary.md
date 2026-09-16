# Pi vs OMP harness benchmark — results

Baseline: `095a664e7fb8519a69e0bff9f0b1d452c26e4cf1` | valid trials: 48 | task budget: 300s

## Baseline harness context (trivial prompt, thinking off)

Total tokens on a one-token reply = harness system prompt plus loaded skills/rules for this checkout; uncached input shown from a cold cache run.

| Arm | Harness | Reps | Median context tokens | Uncached input | Raw total |
| --- | --- | --- | --- | --- | --- |
| omp | omp/18.2.0 | 3 | 21844 | 21843 | [21844, 21844, 21844] |
| pi | 0.85.1 | 3 | 17340 | 17339 | [17340, 17340, 17340] |

## Per-trial results

| Arm | Model | Thinking | Task | Wall s | Reqs | Input | Output | Cache read | Total | Cost | Acceptance | Participant | Scope | Stop |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| omp | deepseek-flash | high | bugfix | 22.9 | 8 | 28377 | 3480 | 177536 | 209393 | $0.0069 | 10 PASS | 4 PASS | ok | exit 0 |
| pi | deepseek-flash | high | bugfix | 21.9 | 9 | 13402 | 2941 | 173184 | 189527 | $0.0086 | 10 PASS | 2 PASS | ok | exit 0 |
| omp | deepseek-flash | high | feature | 34.3 | 7 | 4939 | 5672 | 178560 | 189171 | $0.0047 | 12 PASS | 3 PASS | ok | exit 0 |
| pi | deepseek-flash | high | feature | 21.5 | 9 | 14070 | 3107 | 176512 | 193689 | $0.0090 | 12 PASS | 5 PASS | ok | exit 0 |
| omp | deepseek-flash | high | refactor | 47.8 | 12 | 8952 | 8462 | 344960 | 362374 | $0.0075 | 10 PASS | 1 PASS | ok | exit 0 |
| pi | deepseek-flash | high | refactor | 23.8 | 9 | 14469 | 3996 | 185088 | 203553 | $0.0102 | 10 PASS | 4 PASS | ok | exit 0 |
| omp | deepseek-flash | medium | bugfix | 16.1 | 8 | 25626 | 1889 | 172160 | 199675 | $0.0055 | 10 PASS | 3 PASS | ok | exit 0 |
| pi | deepseek-flash | medium | bugfix | 13.7 | 8 | 13252 | 1493 | 148864 | 163609 | $0.0067 | 10 PASS | 2 PASS | ok | exit 0 |
| omp | deepseek-flash | medium | feature | 17.0 | 6 | 4038 | 2601 | 144128 | 150767 | $0.0026 | 12 PASS | 6 PASS | ok | exit 0 |
| pi | deepseek-flash | medium | feature | 17.7 | 6 | 13534 | 3001 | 113536 | 130071 | $0.0083 | 12 PASS | 8 PASS | ok | exit 0 |
| omp | deepseek-flash | medium | refactor | 35.2 | 9 | 6032 | 5993 | 240256 | 252281 | $0.0052 | 10 PASS | none | ok | exit 0 |
| pi | deepseek-flash | medium | refactor | 28.3 | 10 | 16832 | 4571 | 218624 | 240027 | $0.0118 | 10 PASS | 5 PASS | ok | exit 0 |
| omp | gpt-5.6-luna | high | bugfix | 109.4 | 15 | 41893 | 3977 | 399360 | 445230 | $0.0211 | 10 PASS | 1 PASS | ok | exit 0 |
| pi | gpt-5.6-luna | high | bugfix | 103.2 | 12 | 61439 | 3694 | 247808 | 312941 | $0.0217 | 10 PASS | 1 PASS | ok | exit 0 |
| omp | gpt-5.6-luna | high | feature | 120.1 | 11 | 37772 | 5111 | 284672 | 327555 | $0.0194 | 12 PASS | 3 PASS | ok | exit 0 |
| pi | gpt-5.6-luna | high | feature | 103.9 | 13 | 36444 | 4417 | 283648 | 324509 | $0.0183 | 12 PASS | 3 PASS | ok | exit 0 |
| omp | gpt-5.6-luna | high | refactor | 120.4 | 10 | 34457 | 4467 | 241152 | 280076 | $0.0171 | 10 PASS | none | ok | exit 0 |
| pi | gpt-5.6-luna | high | refactor | 151.3 | 9 | 58800 | 5974 | 160768 | 225542 | $0.0221 | 10 PASS | none | ok | exit 0 |
| omp | gpt-5.6-luna | medium | bugfix | 50.4 | 10 | 52900 | 1711 | 203776 | 258387 | $0.0167 | 10 PASS | 1 PASS | ok | exit 0 |
| pi | gpt-5.6-luna | medium | bugfix | 67.2 | 12 | 33173 | 2490 | 267776 | 303439 | $0.0150 | 10 PASS | 1 PASS | ok | exit 0 |
| omp | gpt-5.6-luna | medium | feature | 70.2 | 8 | 58407 | 2252 | 147456 | 208115 | $0.0173 | 12 PASS | 3 PASS | ok | exit 0 |
| pi | gpt-5.6-luna | medium | feature | 87.7 | 14 | 74919 | 3142 | 214528 | 292589 | $0.0230 | 12 PASS | 3 PASS | ok | exit 0 |
| omp | gpt-5.6-luna | medium | refactor | 68.8 | 12 | 35608 | 2715 | 270848 | 309171 | $0.0158 | 10 PASS | none | ok | exit 0 |
| pi | gpt-5.6-luna | medium | refactor | 85.8 | 10 | 60478 | 3431 | 180224 | 244133 | $0.0198 | 10 PASS | none | ok | exit 0 |
| omp | gpt-5.6-sol | high | bugfix | 90.1 | 9 | 30326 | 3118 | 209792 | 243236 | $0.2676 | 10 PASS | 1 PASS | ok | exit 0 |
| pi | gpt-5.6-sol | high | bugfix | 128.0 | 15 | 34448 | 3540 | 376192 | 414180 | $0.4665 | 10 PASS | 1 PASS | ok | exit 0 |
| omp | gpt-5.6-sol | high | feature | 120.3 | 11 | 33181 | 4784 | 267136 | 305101 | $0.3353 | 12 PASS | 3 PASS | ok | exit 0 |
| pi | gpt-5.6-sol | high | feature | 146.1 | 11 | 34135 | 4359 | 250752 | 289246 | $0.4268 | 12 PASS | 2 PASS | ok | exit 0 |
| omp | gpt-5.6-sol | high | refactor | 189.6 | 11 | 33126 | 6466 | 260224 | 299816 | $0.3659 | 10 PASS | none | ok | exit 0 |
| pi | gpt-5.6-sol | high | refactor | 138.5 | 13 | 32507 | 4206 | 291200 | 327913 | $0.4343 | 10 PASS | none | ok | exit 0 |
| omp | gpt-5.6-sol | medium | bugfix | 89.0 | 10 | 31070 | 2881 | 239232 | 273183 | $0.2776 | 10 PASS | 1 PASS | ok | exit 0 |
| pi | gpt-5.6-sol | medium | bugfix | 78.9 | 10 | 29988 | 2404 | 221568 | 253960 | $0.3328 | 10 PASS | 1 PASS | ok | exit 0 |
| omp | gpt-5.6-sol | medium | feature | 88.1 | 9 | 28147 | 3321 | 190976 | 222444 | $0.2554 | 12 PASS | 3 PASS | ok | exit 0 |
| pi | gpt-5.6-sol | medium | feature | 82.5 | 10 | 29644 | 2938 | 211328 | 243910 | $0.3420 | 12 PASS | 2 PASS | ok | exit 0 |
| omp | gpt-5.6-sol | medium | refactor | 96.4 | 8 | 29193 | 3342 | 174720 | 207255 | $0.2535 | 10 PASS | none | ok | exit 0 |
| pi | gpt-5.6-sol | medium | refactor | 93.3 | 7 | 24600 | 3258 | 115456 | 143314 | $0.2785 | 10 PASS | none | ok | exit 0 |
| omp | gpt-6-astra | high | bugfix | 81.6 | 9 | 30055 | 1718 | 207360 | 239133 | $0.5938 | 10 PASS | 1 PASS | ok | exit 0 |
| pi | gpt-6-astra | high | bugfix | 89.7 | 9 | 30293 | 1853 | 193280 | 225426 | $0.5889 | 10 PASS | 1 PASS | ok | exit 0 |
| omp | gpt-6-astra | high | feature | 86.8 | 9 | 29936 | 1898 | 203520 | 235354 | $0.5978 | 12 PASS | 4 PASS | ok | exit 0 |
| pi | gpt-6-astra | high | feature | 88.5 | 10 | 32424 | 2180 | 218752 | 253356 | $0.6520 | 12 PASS | 4 PASS | ok | exit 0 |
| omp | gpt-6-astra | high | refactor | 96.4 | 8 | 29023 | 2278 | 168448 | 199749 | $0.5726 | 10 PASS | none | ok | exit 0 |
| pi | gpt-6-astra | high | refactor | 78.6 | 6 | 24892 | 2044 | 98176 | 125112 | $0.4493 | 10 PASS | none | ok | exit 0 |
| omp | gpt-6-astra | medium | bugfix | 64.7 | 11 | 28999 | 1121 | 246400 | 276520 | $0.5924 | 10 PASS | 1 PASS | ok | exit 0 |
| pi | gpt-6-astra | medium | bugfix | 85.2 | 10 | 30954 | 1676 | 220160 | 252790 | $0.6135 | 10 PASS | 1 PASS | ok | exit 0 |
| omp | gpt-6-astra | medium | feature | 79.8 | 10 | 26694 | 1459 | 206336 | 234489 | $0.5462 | 12 PASS | 4 PASS | ok | exit 0 |
| pi | gpt-6-astra | medium | feature | 93.6 | 8 | 27958 | 1856 | 153600 | 183414 | $0.5260 | 12 PASS | 3 PASS | ok | exit 0 |
| omp | gpt-6-astra | medium | refactor | 90.7 | 9 | 30976 | 2157 | 206592 | 239725 | $0.6242 | 10 PASS | none | ok | exit 0 |
| pi | gpt-6-astra | medium | refactor | 97.9 | 9 | 28320 | 2261 | 176896 | 207477 | $0.5731 | 10 PASS | 2 PASS | ok | exit 0 |

## Aggregate per arm × model × thinking

| Arm | Model | Thinking | Tasks passed | Wall s (sum) | Wall s (median) | Total tokens | Input | Output | Cost | Model mismatch |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| omp | deepseek-flash | high | 3/3 | 105.0 | 34.3 | 760938 | 42268 | 17614 | $0.0190 | no |
| omp | deepseek-flash | medium | 3/3 | 68.2 | 17.0 | 602723 | 35696 | 10483 | $0.0133 | no |
| omp | gpt-5.6-luna | high | 3/3 | 349.9 | 120.1 | 1052861 | 114122 | 13555 | $0.0576 | no |
| omp | gpt-5.6-luna | medium | 3/3 | 189.4 | 68.8 | 775673 | 146915 | 6678 | $0.0498 | no |
| omp | gpt-5.6-sol | high | 3/3 | 400.0 | 120.3 | 848153 | 96633 | 14368 | $0.9688 | no |
| omp | gpt-5.6-sol | medium | 3/3 | 273.5 | 89.0 | 702882 | 88410 | 9544 | $0.7865 | no |
| omp | gpt-6-astra | high | 3/3 | 264.8 | 86.8 | 674236 | 89014 | 5894 | $1.7642 | no |
| omp | gpt-6-astra | medium | 3/3 | 235.2 | 79.8 | 750734 | 86669 | 4737 | $1.7629 | no |
| pi | deepseek-flash | high | 3/3 | 67.2 | 21.9 | 586769 | 41941 | 10044 | $0.0278 | no |
| pi | deepseek-flash | medium | 3/3 | 59.7 | 17.7 | 533707 | 43618 | 9065 | $0.0268 | no |
| pi | gpt-5.6-luna | high | 3/3 | 358.4 | 103.9 | 862992 | 156683 | 14085 | $0.0621 | no |
| pi | gpt-5.6-luna | medium | 3/3 | 240.7 | 85.8 | 840161 | 168570 | 9063 | $0.0578 | no |
| pi | gpt-5.6-sol | high | 3/3 | 412.6 | 138.5 | 1031339 | 101090 | 12105 | $1.3277 | no |
| pi | gpt-5.6-sol | medium | 3/3 | 254.6 | 82.5 | 641184 | 84232 | 8600 | $0.9533 | no |
| pi | gpt-6-astra | high | 3/3 | 256.8 | 88.5 | 603894 | 87609 | 6077 | $1.6901 | no |
| pi | gpt-6-astra | medium | 3/3 | 276.6 | 93.6 | 643681 | 87232 | 5793 | $1.7126 | no |

## Harness headline (all models and levels together)

| Arm | Trials | Acceptance | Wall s (sum) | Wall s (median) | Total tokens | Input | Output | Cost | Scope violations | Deadlines |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| omp | 24 | 24/24 | 1885.9 | 86.8 | 6168200 | 699727 | 82873 | $5.4220 | 0 | 0 |
| pi | 24 | 24/24 | 1926.7 | 87.7 | 5743727 | 770975 | 74832 | $5.8584 | 0 | 0 |

## Same-model pairing (Pi minus OMP)

| Model | Thinking | Task | Acceptance (Pi/OMP) | Wall s (Pi/OMP) | Tokens (Pi/OMP) | Cost (Pi/OMP) |
| --- | --- | --- | --- | --- | --- | --- |
| deepseek-flash | high | bugfix | P/P | 21.9/22.9 | 189527/209393 | $0.0086/$0.0069 |
| deepseek-flash | high | feature | P/P | 21.5/34.3 | 193689/189171 | $0.0090/$0.0047 |
| deepseek-flash | high | refactor | P/P | 23.8/47.8 | 203553/362374 | $0.0102/$0.0075 |
| deepseek-flash | medium | bugfix | P/P | 13.7/16.1 | 163609/199675 | $0.0067/$0.0055 |
| deepseek-flash | medium | feature | P/P | 17.7/17.0 | 130071/150767 | $0.0083/$0.0026 |
| deepseek-flash | medium | refactor | P/P | 28.3/35.2 | 240027/252281 | $0.0118/$0.0052 |
| gpt-5.6-luna | high | bugfix | P/P | 103.2/109.4 | 312941/445230 | $0.0217/$0.0211 |
| gpt-5.6-luna | high | feature | P/P | 103.9/120.1 | 324509/327555 | $0.0183/$0.0194 |
| gpt-5.6-luna | high | refactor | P/P | 151.3/120.4 | 225542/280076 | $0.0221/$0.0171 |
| gpt-5.6-luna | medium | bugfix | P/P | 67.2/50.4 | 303439/258387 | $0.0150/$0.0167 |
| gpt-5.6-luna | medium | feature | P/P | 87.7/70.2 | 292589/208115 | $0.0230/$0.0173 |
| gpt-5.6-luna | medium | refactor | P/P | 85.8/68.8 | 244133/309171 | $0.0198/$0.0158 |
| gpt-5.6-sol | high | bugfix | P/P | 128.0/90.1 | 414180/243236 | $0.4665/$0.2676 |
| gpt-5.6-sol | high | feature | P/P | 146.1/120.3 | 289246/305101 | $0.4268/$0.3353 |
| gpt-5.6-sol | high | refactor | P/P | 138.5/189.6 | 327913/299816 | $0.4343/$0.3659 |
| gpt-5.6-sol | medium | bugfix | P/P | 78.9/89.0 | 253960/273183 | $0.3328/$0.2776 |
| gpt-5.6-sol | medium | feature | P/P | 82.5/88.1 | 243910/222444 | $0.3420/$0.2554 |
| gpt-5.6-sol | medium | refactor | P/P | 93.3/96.4 | 143314/207255 | $0.2785/$0.2535 |
| gpt-6-astra | high | bugfix | P/P | 89.7/81.6 | 225426/239133 | $0.5889/$0.5938 |
| gpt-6-astra | high | feature | P/P | 88.5/86.8 | 253356/235354 | $0.6520/$0.5978 |
| gpt-6-astra | high | refactor | P/P | 78.6/96.4 | 125112/199749 | $0.4493/$0.5726 |
| gpt-6-astra | medium | bugfix | P/P | 85.2/64.7 | 252790/276520 | $0.6135/$0.5924 |
| gpt-6-astra | medium | feature | P/P | 93.6/79.8 | 183414/234489 | $0.5260/$0.5462 |
| gpt-6-astra | medium | refactor | P/P | 97.9/90.7 | 207477/239725 | $0.5731/$0.6242 |
