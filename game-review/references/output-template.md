# Output template (sections A-F)

Use this structure for every full review. Lead with the verdict. Keep each match block compact and evidence-dense; omit nothing from the field list, but write "not found" where data was unavailable rather than padding. Cite sources inline for injuries, suspensions, lineups, and any statistic that drives a probability.

---

## A. Executive Summary

- **Matches / legs reviewed**: N (note any settled, live, or void legs)
- **Overall assessment**: 2-3 sentences, plain language
- **Strongest selection**: leg, probability, why
- **Weakest selection**: leg, probability, why
- **Most concerning injury or lineup issue**: player, status grade ([Confirmed] / [Reported] / [Speculation] / [Not found]), source, effect on the exact market
- **Estimated probability the whole ticket wins**: point estimate and range, against the breakeven probability implied by the combined odds
- **Verdict**: **Keep / Modify / Reject**, one-line reason

## B. Individual Match Analysis

Repeat for every match, in ticket order. Fields:

1. **Match and competition** (start time in the user's timezone)
2. **Exact selection and odds**, plus the one-sentence winning condition
3. **Recent form and relevant statistics** (opponent quality, market-relevant rates, underlying metrics)
4. **Home/away or venue/surface performance**
5. **Injury, suspension, and lineup report** (grade every item; cite source and time)
6. **Tactical and contextual analysis** (motivation, schedule, conditions, developments)
7. **Key arguments supporting the selection**
8. **Key arguments against the selection** (include plausible losing scenarios)
9. **Estimated probability of winning**: point estimate and range, basis labelled (statistical / market-implied / judgement), key assumptions
10. **Bookmaker-implied probability** (raw, and margin-removed where a full market was available; say which)
11. **Risk classification**: Strong / Reasonable / Questionable / Poor
12. **Verdict**: Keep / Replace / Remove
13. **Best alternative market**, only if the evidence justifies it, with the probability-versus-payout trade-off

## C. Ranked Selection Table

Strongest to weakest. Explain any close calls under the table.

| Rank | Match | Selection | Odds | Estimated Win Probability | Main Risk | Verdict |
|---|---|---|---|---|---|---|

## D. Ticket-Level Risk Analysis

- Combined odds (pending legs plus won legs; void legs removed)
- Estimated overall probability of winning (point and range) and the breakeven probability
- Probability that at least one leg loses, and how the number of legs drives it
- The weakest links and their contribution to overall risk (leave-one-out figures from `scripts/odds_math.py`)
- Correlations between selections and the direction of the bias they introduce
- Whether the potential payout justifies the risk (expected return per unit staked)
- Effect of removing or replacing questionable selections

## E. Recommended Final Ticket

- **Retain**: legs kept, one line each
- **Remove**: legs dropped, with the reason
- **Replace**: replacements, only where the evidence supports them, with the trade-off stated
- Why this version is better supported by the evidence
- New combined odds and probability for the recommended ticket
- If no selection offers convincing value, say so here instead of forcing a recommendation. Do not add legs to raise the payout.

## F. Sources and Uncertainties

- **Sources**: link, outlet, and published/updated time for the items that matter most (injuries, suspensions, lineups, odds, key statistics)
- **Not verified**: items you looked for and could not confirm, and how each could change the conclusion
- **Late-news risk**: which legs are most sensitive to lineup or injury news and when to recheck (before start)
- **Data path used**: ESPN API, web search, or other tools (one line), and any gaps that came from it
- **Settlement rules**: markets where the user should confirm the bookmaker's rules (overtime, retirement, void conditions, player did not play)
- A closing line that no outcome is certain and that the probabilities are estimates

---

## Discovery output (when the user only asked what is on)

A compact table, soonest first, grouped by league:

| Start (user TZ) | League | Match | Status | Market reference (if available) |
|---|---|---|---|---|

State the data path used. Offer to review any game, a shortlist, or all of them. Do not rank "best bets" unless asked.
