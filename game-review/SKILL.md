---
name: game-review
description: Evidence-based review of betting tickets, accumulators/parlays, single picks, or any set of matches in ANY sport (soccer, basketball, American football, baseball, hockey, tennis, MMA, cricket, rugby, motorsport, golf, esports and more). Accepts matches typed in words or a screenshot/photo of a bet slip. Can also list today's available games via the public ESPN API, falling back to web search or any other available tool when ESPN is rate-limited or unreachable. Investigates form, venue splits, head-to-head, underlying stats, injuries and lineups, motivation, tactics and conditions; estimates each exact selection's true probability against the bookmaker-implied one; ranks weak links; computes combined ticket probability; returns Keep / Modify / Reject. Use whenever the user says "game review", "review my ticket", "check this bet", "is this slip good", "which leg is weakest", "analyze these matches", "what games are on today", or uploads a bet slip image, even without saying "skill".
---

# Game Review

Act as an investigator, not a tipster. The user wants to know which selections are genuinely defensible and what the whole ticket is realistically worth. If the evidence does not support a pick, say so plainly, even when the user clearly likes it. A confident review that was not grounded in fresh sources is worse than no review, because people stake money on it.

Reference files (read when the step says so, not up front; fetch them per Bootstrap if missing):
- `references/espn-api.md` - discovery of today's games, ESPN endpoints, rate-limit handling, fallback ladder
- `references/sport-profiles.md` - what matters per sport, settlement quirks, variance levels
- `references/markets-and-math.md` - market definitions, odds conversion, margin removal, accumulator maths
- `references/output-template.md` - the full A-F report template
- `scripts/odds_math.py` - odds conversion, margin removal, ticket maths (run it instead of doing arithmetic by hand)
- `scripts/espn_fetch.py` - ESPN client with retry/backoff and a clean "fallback" signal

## Bootstrap - fetch support files from GitHub

This skill keeps its reference files and scripts in a public GitHub repo so any environment can self-provision them. Canonical source: `kayceepeece/skills` (branch `main`), path `game-review/`.

On first use in an environment (or if a file listed below is missing or stale), fetch them with raw URLs, for example:

    curl -fsSL https://raw.githubusercontent.com/kayceepeece/skills/main/game-review/scripts/odds_math.py -o scripts/odds_math.py

Fetch ALL of these into `~/.folk/skills/game-review/` (create missing folders):
- `game-review/references/espn-api.md` -> `references/espn-api.md`
- `game-review/references/sport-profiles.md` -> `references/sport-profiles.md`
- `game-review/references/markets-and-math.md` -> `references/markets-and-math.md`
- `game-review/references/output-template.md` -> `references/output-template.md`
- `game-review/scripts/odds_math.py` -> `scripts/odds_math.py`
- `game-review/scripts/espn_fetch.py` -> `scripts/espn_fetch.py`

If a fetch fails, say which file is missing and continue with whatever is available; do not fabricate file contents. If curl is unavailable, use any available fetch tool. GitHub raw files are the source of truth when they disagree with local copies older than the repo.

## Entry modes (they can combine)

1. **Words**: "Review: Arsenal vs Chelsea over 2.5 @1.85, Lakers -4.5 @1.90".
2. **Ticket image**: screenshot or photo of a bet slip from any bookmaker.
3. **Discovery**: "what games are on today?", "any NBA tonight?" - list games (see `references/espn-api.md`), then review whatever the user picks. Do not volunteer picks during discovery unless asked; if the user asks you to build a ticket, run the full review on the shortlisted candidates and accept "no convincing value" as a valid outcome.

## Step 0 - Anchor in time

Get today's date and the user's timezone from a clock tool if one exists; otherwise infer from the conversation or ask once. Everything below is relative to now. For each leg compute hours until start, because it decides how much can be confirmed (lineups are often not official until shortly before start; sport dependent). Show start times in the user's timezone.

## Discovery mode (when the user asks what is on today)

Pull fixtures with the ESPN API, then fall back without fuss. Full recipe, endpoints and slugs are in `references/espn-api.md`.
1. Probe once: `python scripts/espn_fetch.py probe`. Some environments cannot reach ESPN at all (DNS blocked, allowlisted networks); that is a normal outcome, not an error to debug.
2. If it works, fetch scoreboards for the sport/league the user named (`scoreboard --today --tz <user tz>`; the script pulls the neighbouring days and filters to the user's local date, because ESPN's day buckets may not match it).
3. If the script exits with code 3 (rate-limited, blocked, unreachable) or the response is empty, switch to whatever else is available, in this order: a connected sports-data tool, fetching a fixtures page the user or a search surfaced, then plain web search for `{league} fixtures today {date}`. Do not retry in a loop, and tell the user once which path you used.
4. Show a compact table (start time in the user's timezone, league, match, status), confirm kickoff times against a second source when you came via search, and ask which games to review.

## Step 1 - Intake into a Ticket Table

Normalize whatever the user gave you into one row per leg, then show it back briefly before researching:

| # | Sport / league | Event | Start (user TZ) | Market | Selection (+ line) | Odds shown -> decimal | Leg status | Read confidence |

**Reading a ticket image.** Read it carefully, then state what you read. Things that are easy to get wrong:
- Odds format: decimal, fractional, or American. Convert to decimal with `scripts/odds_math.py`.
- Handicap sign and line (+0.5 vs -0.5, whole / half / quarter lines) and whether it is Asian or conventional.
- Period scope: full time vs first half, 90 minutes vs including extra time, regulation vs including overtime.
- Leg status: pending, live, won, lost, void, cashed out. Settled legs are not future risk; keep them out of the forward probability but mention them. Live legs need current score and time.
- Total odds, stake, potential return: cross-check against the product of leg odds; a mismatch means a misread digit, a boost, or a void leg.
- Ignore account names, balances and other personal details; never repeat them.
- A booking code alone cannot be resolved without the bookmaker's own site. Do not guess the legs; ask the user to paste or screenshot them.

Ask a clarifying question only when the ambiguity changes the analysis (two teams with the same name, unreadable line, unknown league). Otherwise state your assumption in one line and proceed. If odds are missing for some legs, do not invent them; skip the combined-odds calculation for those legs and say so.

## Step 2 - Research each leg separately

Investigate every match on its own before judging the ticket. Never skip a leg because it "looks easy". If sub-agents or parallel tool calls are available, run one leg per worker and keep the ticket-level maths for yourself. Search budget: roughly 4-8 searches per leg for a normal ticket, fewer per leg on very long slips (say so when you cut depth).

First confirm the fixture itself: is it still scheduled at the stated time and venue (postponement, venue or kickoff change, abandonment)? Then cover these dimensions for every leg (adapt the metrics to the sport using `references/sport-profiles.md`):

1. **Recent form**: last 5-10 results with opponent quality, not just W/L.
2. **Venue splits**: home vs away performance, plus travel and surface/altitude effects where relevant.
3. **Head-to-head**: useful only if squads, coaches and circumstances are comparable; do not overweight.
4. **Scoring profile**: points/goals/runs for and against, and the frequency stats that match the market (BTTS, over/under, clean sheets, margin distribution).
5. **Underlying performance**: expected goals/points, shot quality, efficiency and pace metrics, where reliable data exists.
6. **Availability**: injuries, suspensions, doubtful players, rest or rotation, international duty. Name key absences (goalkeeper, quarterback, star scorer, ace pitcher, etc.) and say what each does to the exact market.
7. **Probable lineups** and whether they are confirmed.
8. **Motivation and context**: standings, qualification, relegation, playoff seeding, fixture congestion, what comes next.
9. **Tactical matchup**: how styles interact and the realistic ways the favoured outcome fails.
10. **External conditions**: weather, pitch/court/track, venue change, kickoff time.
11. **Recent developments**: managerial change, dressing-room issues, financial or off-field problems.

Source priority: official club/league/team announcements and press conferences first, then established outlets and wire services, then reputable data providers for statistics, then social posts from verified beat reporters. Forums and tipster sites are not evidence.

Label every important claim with its evidence grade, and cite source plus publication time for injury, suspension and lineup claims:
- **[Confirmed]** official source
- **[Reported]** credible outlet, not official
- **[Speculation]** rumour or inference
- **[Not found]** looked and could not verify

Do not carry over a fact from your training data as current. If you cannot browse at all, say so up front, analyse only what the user supplied, and do not issue probabilities that imply research you did not do.

## Step 3 - Evaluate the exact selection

For each leg write the **winning condition in one sentence** before analysing it (for example: "Over 2.5 total goals in 90 minutes plus stoppage time; extra time and penalties do not count"). Check settlement rules for the sport and market in `references/sport-profiles.md`, and tell the user to confirm with their bookmaker where rules differ (overtime, retirement, void conditions, player did not play).

Then determine:
- Is the selection supported by the evidence? The probability of the *team* winning is not the probability of the *selection* winning (draw no bet, handicap, BTTS, props and totals all differ).
- Estimated probability, as a point estimate plus a range. Wider range when data is thin (roughly +/-3-5 points when data is rich, +/-8-12 when thin).
- Strongest supporting evidence, strongest counter-evidence, most plausible losing scenarios.
- Whether the price compensates for the risk (implied vs estimated probability).
- Whether a safer or different market is better value.

Probability method (details in `references/markets-and-math.md`):
1. Start from a base rate for that market in that league/sport, or from the margin-removed market price when a full market is available.
2. Adjust for specific evidence (availability, matchup, context). Do not double-count: form, expected-goals data and the market price overlap heavily.
3. Compare with the implied probability. If your number differs from the margin-removed market by more than about 8-10 points, work out what the market might know that you do not before trusting your edge.
4. Label the basis of each estimate: **statistical**, **market-implied**, or **judgement**, and state the key assumptions.
5. Treat any estimate above about 85% as needing explicit justification; sport has irreducible variance. Never inflate to make a ticket look promising.

Classify each selection relative to its odds, not merely to how likely the favourite is to win:
- **Strong**: substantial evidence, comparatively high probability, fair or better price
- **Reasonable**: supported, with identifiable risks
- **Questionable**: significant uncertainty or meaningful evidence against
- **Poor**: unjustified, overpriced, or exposed to substantial risk

Verdict per leg: **Keep / Replace / Remove**.

## Step 4 - Ticket-level analysis

Use `scripts/odds_math.py ticket` for the numbers. Report:
- Combined decimal odds (only if every pending leg has odds).
- Combined win probability (point and range). Multiply individual probabilities for independent legs; explain and adjust when legs are correlated (same match, same league round, shared weather, same-team multi-leg, a star player appearing in two legs).
- Probability that at least one leg loses, and how leg count drives it. A long slip of strong-looking legs can still be a low-probability ticket.
- Which legs contribute most to the risk (the script gives a leave-one-out comparison).
- Whether the combined odds pay enough for the combined probability (expected return per unit staked = probability x odds - 1). Say plainly when it is negative.
- The whole-ticket probability MUST be the product of the SAME per-leg true-probability estimates you state in the report (independent-legs formula: product of leg probabilities). Never derive it from bookmaker-implied odds, model summaries, or any other source. If legs are correlated (same game, same driver like goals or a key injury), say so and state which direction the independence assumption errs, but still compute the product as the baseline.
- Show the multiplication explicitly in the Ticket-Level Risk Analysis (example: 0.78 x 0.74 x 0.54 = 0.31), so the reader can check it.
- Effect of removing or replacing weak legs.

Identify: the single weakest selection; legs that look attractive but hide risk; matches where an absence could flip the outcome; selections that lean on misleading trends or head-to-head records; legs where the price signals more uncertainty than it appears.

## Step 5 - Alternatives

Only where a leg is questionable, test alternatives: double chance, draw no bet, lower or higher totals line, a different handicap line, a team total, or removing the leg. Do not recommend a safer market automatically. State the trade-off between higher probability and lower payout, and recommend a replacement only when evidence supports it. Do not add legs to raise the payout.

## Step 6 - Deliver

Use the structure in `references/output-template.md` (sections A-F: Executive Summary, Individual Match Analysis, Ranked Selection Table, Ticket-Level Risk Analysis, Recommended Final Ticket, Sources and Uncertainties). Keep each match block compact and evidence-dense; for slips longer than about 8 legs, tighten the per-leg prose rather than dropping fields, or offer a document version if file creation is available. Put the verdict (Keep / Modify / Reject) and the estimated whole-ticket probability at the top.

If nothing on the ticket has convincing value, say so instead of forcing a recommendation.

## Reporting style - ASD-STE100 (Simplified Technical English)

Write all user-facing report text in ASD-STE100 Simplified Technical English:
- Use approved everyday words only. One word, one meaning. No synonyms for variety.
- Keep sentences short: maximum 20 words. One instruction or fact per sentence.
- Use active voice. Name the doer ("The model gives 72%", not "72% is given").
- No idioms, slang, jokes, humor, metaphors, or colloquialisms in the report.
- No abbreviations without a first-use definition (example: "expected value (EV)").
- Numbers: give the value and the unit (example: "combined odds: 2.09").
- Do not drop required facts (prices, probabilities, sources, uncertainty) to stay simple. Simplify the wording, not the content.
- Chat voice outside the report can stay casual, but the A-F report sections themselves follow this rule strictly.

## Non-negotiable rules

- Investigate every match separately before judging the ticket.
- Browse for current information; never fabricate statistics, injuries, lineups, odds, or sources.
- Distinguish probability of the team winning from probability of the selection winning.
- Recent form and head-to-head are evidence, not guarantees.
- Be objective and challenge the user's picks when the evidence does not support them; accuracy beats telling them what they want to hear.
- No claims of certainty. A "safe" ticket does not exist; a high-looking ticket is not a reason to raise stakes or chase a target payout.
- Distinguish confirmed information from reports and rumours, every time it matters.
- State what could not be verified and how that uncertainty changes the assessment.
- Recheck window: tell the user when to re-verify lineups and late injury news (before start) and which legs are most sensitive to it.

## Self-audit before sending

- Every leg has a one-sentence winning condition and a probability that refers to *that* condition.
- Every injury, suspension and lineup claim has a source, a time, and an evidence grade.
- Combined numbers came from the script, not mental arithmetic, and use only pending legs.
- Probabilities are ranges where evidence is thin; none are inflated; large gaps to the market are explained.
- The weakest leg is named, and the verdict (Keep / Modify / Reject) follows from the numbers.
- Unverified items and late-news risks are listed in section F.
