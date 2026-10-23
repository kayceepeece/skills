# Markets and maths

Contents: 1) odds formats, 2) implied probability and margin, 3) market definitions that are often confused, 4) estimating probability, 5) accumulators and correlation, 6) script usage

## 1. Odds formats

| Format | Example | To decimal |
|---|---|---|
| Decimal | 1.85 | as is |
| Fractional | 5/4 | 1 + 5/4 = 2.25 |
| American | -150 / +130 | 1 + 100/150 = 1.667 / 1 + 130/100 = 2.30 |

Decimal odds include the returned stake. Always work in decimal.

## 2. Implied probability and margin

Implied probability = 1 / decimal odds. 1.85 implies 54.1%. That number **includes the bookmaker's margin**.

If you have every outcome of a market (e.g. home/draw/away), the implied probabilities sum to more than 100%. The excess is the overround (margin). Remove it to get a fairer estimate:
- **Proportional (multiplicative)**: divide each implied probability by the sum. Simple, slightly over-credits longshots.
- Power/Shin methods are better at the favourite-longshot bias but need the script's `--method power` option or specialist tools; state which you used.

If you only have **one price** (the usual case on a ticket, e.g. over 2.5 at 1.85), you cannot remove the margin exactly. Either find the opposite side of the market (under 2.5 price) and de-vig the pair, or say you are using the raw implied probability and that the fair probability is somewhat lower (for typical two-way markets the margin often sits in the low single digits percent; do not quote a specific margin unless you found it). Never present a single raw implied probability as the "true" probability.

Distinguish three kinds of numbers in the report: **market-implied** (from odds), **statistical** (from base rates or models you can cite), **judgement** (your weighted view). Label each.

## 3. Markets that get confused

- **Home win / 1X2**: three-way, 90 minutes (soccer) unless stated. A draw loses.
- **Double chance (1X, X2, 12)**: two of three outcomes win; probability is the sum of the two outcomes. Much shorter odds.
- **Draw no bet**: draw refunds the stake; win = win, loss = loss. Probability of winning the bet is P(win) / (1 - P(draw)) in terms of *settled* outcomes, but the refund still carries an opportunity cost.
- **Over/Under X.5**: no push. **Over/Under X.0** (whole number): exact total refunds. **Quarter lines (X.25, X.75)**: stake splits across two adjacent lines.
- **Both teams to score**: both must score at least once in the settlement period; own goals do not count for the scoring team, depending on the bookmaker's rules (check).
- **Team to score / team total**: individual team threshold, not BTTS.
- **Full time vs first half vs second half**: separate markets; half-time results are lower-probability than full-time for the same team.
- **Conventional (European) handicap**: three-way with a draw outcome after the handicap. **Asian handicap**: two-way, whole lines refund when the margin equals the line, half lines cannot push, quarter lines split the stake.
- **Moneyline / match winner (two-way sports)**: overtime/extra periods normally count in basketball, American football, baseball extra innings, and usually hockey overtime/shootout. Check each.
- **Player props**: depend on the player starting and playing; rules for did-not-play vary by sport and bookmaker.

## 4. Estimating probability

1. Find a base rate for the exact market: league-level frequency of the outcome this season and last (e.g. proportion of matches with 3+ goals, proportion of favourites at similar prices that cover the spread).
2. Adjust for the specifics: team strength, matchup, availability, context, conditions. Each adjustment needs a reason you can cite.
3. Cross-check against the de-vigged market. A gap greater than roughly 8-10 points means either you found real information or you are missing something; investigate which before trusting yourself.
4. Express as a point estimate and a range. Range width reflects data quality, not a guess at precision.
5. Avoid double-counting: form, expected goals, and the market price are correlated views of the same underlying strength.

## 5. Accumulators and correlation

For independent legs: combined odds = product of leg decimal odds; combined probability = product of leg probabilities.
- Probability at least one leg loses = 1 - combined probability. This climbs fast with leg count: ten legs at 80% each win together about 11% of the time.
- Expected return per unit staked = combined probability x combined odds - 1. A negative figure means the payout does not compensate for the risk at your estimated probabilities (the bookmaker margin compounds across legs).
- **Correlation**: legs in the same match (e.g. a team win with over 2.5 goals) are positively correlated, so the joint probability is usually higher than the product of the individual probabilities; many bookmakers price or block this. Legs sharing a cause (same weather system, same star player, same referee tendency, the same team in two markets) are also linked. Conversely, a team to win and under 1.5 goals can be negatively correlated for high-scoring teams. If you adjust, say how and by how much; do not hide a guess inside a number. Default: treat as independent and flag the direction of the bias.
- Settled-won legs have probability 1 (remove from forward-looking risk); void legs drop out and reduce combined odds; lost legs mean the ticket is dead.
- Leave-one-out: compute the ticket without each leg to see how much each leg costs in probability versus how much payout it adds. The script prints this.

## 6. Script usage

```
# Convert and de-vig a full market
python scripts/odds_math.py devig --odds 2.10 3.40 3.60
python scripts/odds_math.py devig --odds 1.85 1.95 --method power

# Convert formats
python scripts/odds_math.py convert --fmt american --value -150
python scripts/odds_math.py convert --fmt fractional --value 5/4

# Ticket maths from JSON (legs with decimal odds and your probability or range)
python scripts/odds_math.py ticket --legs legs.json
```

`legs.json` example:
```
[
  {"name": "Arsenal v Chelsea: Over 2.5", "odds": 1.85, "p": 0.52, "p_low": 0.46, "p_high": 0.58},
  {"name": "Lakers -4.5", "odds": 1.90, "p": 0.50, "p_low": 0.45, "p_high": 0.55, "status": "pending"}
]
```
Use `"status": "won"`, `"lost"` or `"void"` for settled legs. Optional `"group"` labels correlated legs; the script reports them but does not silently adjust.
