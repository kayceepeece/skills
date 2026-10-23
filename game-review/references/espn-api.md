# ESPN API reference for game-review

Source: community documentation at https://github.com/pseudo-r/Public-ESPN-API (README footer says last updated July 2026; 17 sports, 139 leagues). These are **unofficial, undocumented** endpoints that power ESPN's own site and apps. They need no authentication, may change without notice, and have no published rate limit ("excessive requests may be blocked"). The endpoint details below come from that documentation and were **not verified live** when this skill was written (the authoring sandbox could not resolve ESPN hosts). Trust what a live response actually returns over this file.

Contents: 1) access ladder, 2) discovery recipe, 3) endpoints, 4) slugs, 5) gotchas, 6) rate-limit etiquette, 7) fallback, 8) what ESPN data is and is not good for

## 1. Access ladder (try in order, stop at the first that works)

Environments differ. Some sandboxes block outbound hosts outside an allowlist, and some fetch tools only open URLs that the user or a prior search surfaced. Probe once, cheaply, then commit.

1. **Direct HTTP from code** (`python scripts/espn_fetch.py probe`, or curl). Best: structured JSON, one call per league.
2. **A fetch/browse tool** that can open the exact URL. If it refuses because the URL was not in the conversation, ask the user to paste the URL, or move on.
3. **A dedicated sports-data tool** if one is connected (scores, schedules, standings). Prefer it over scraping.
4. **Web search and page fetch** of fixtures/results pages (see section 7).

A failed probe (DNS failure, connection refused, HTTP 403/429/5xx, timeout, empty body, non-JSON body, "access denied" page) all mean the same thing: **go down the ladder**. Do not loop, do not hammer. Tell the user once, in a line, which path you used ("ESPN API was unreachable here, so I used web search for today's fixtures"), and keep going.

## 2. Discovery recipe ("what games are available today?")

1. Fix the date window. Use the user's timezone. ESPN event `date` values are UTC ISO timestamps and a day bucket on ESPN's side may not match the user's local calendar day, so request the day before and the day after as well and keep only events whose converted start time falls in the user's "today".
2. Fix the scope. If the user named a sport or league, use it. If they named neither, offer the common ones for their region or ask one short question; avoid scanning all 139 leagues.
3. Pull scoreboards:
   - Single league/day: `GET https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard?dates=YYYYMMDD`
   - Date range: `dates=YYYYMMDD-YYYYMMDD`
   - Breadth across leagues of one sport: the personalized header endpoint `https://site.web.api.espn.com/apis/personalized/v2/scoreboard/header?sport={sport}&region={region}&tz={tz}` is documented as returning `sports[].leagues[].events[]` for active competitions (useful for cricket series and tournaments). Then drill down per league.
   - Fast CDN alternative: `https://cdn.espn.com/core/{sport}/scoreboard?xhr=1` (soccer needs `&league={slug}`).
   - NCAA sports truncate by default: add `groups=50&limit=500` to get the full slate.
4. Normalize rows: league, kickoff (user TZ), home/away (or A/B), status (`pre` / `in` / `post`), venue if present, ESPN odds if present (section 3).
5. Present a compact table grouped by league, soonest first. Mark `in` games as live and `post` games as finished (not bettable). Offer to review any, a shortlist, or all.
6. Do not rank "best bets" during discovery unless asked. If asked, run the full review on candidates.

## 3. Endpoints worth using

Site API (scores, teams, news): `https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/{resource}`

| Resource | Use |
|---|---|
| `scoreboard` (+ `?dates=`) | Fixtures, live scores, results |
| `teams`, `teams/{id}` | Team ids and details |
| `teams/{id}/schedule` | Recent results and upcoming games (form) |
| `teams/{id}/injuries` | Team injury report (a lead, not confirmation) |
| `teams/{id}/roster` | Squad |
| `injuries` | League-wide injuries (documented to work for team sports, including soccer; 500 for MMA/tennis/golf) |
| `summary?event={id}` | Full match package: boxscore, leaders, predictor when available |
| `news` | Latest league news |

Standings: use `https://site.api.espn.com/apis/v2/sports/{sport}/{league}/standings` (**not** `/apis/site/v2/`, which returns a stub or empty `{}`).

Core API: `https://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/...`
- `events/{id}/competitions/{id}/odds` - odds per provider (spread, over/under, moneylines; soccer has three-way prices)
- `events/{id}/competitions/{id}/probabilities` - ESPN win probabilities
- `events/{id}/competitions/{id}/predictor` and `powerindex` - ESPN model outputs (not available for every sport)
- `events/{id}/competitions/{id}/odds` may be empty for smaller leagues
- `seasons/{year}/futures`, `.../ats`, `.../odds-records` - futures and against-the-spread records
- `standings`, `leaders`, `coaches/{id}/record/{type}`

Real-time news: `https://now.core.api.espn.com/v1/sports/news?sport={sport}&leagues={league}&team={abbrev}&limit={n}`

Athlete overview/stats/gamelog/splits: `https://site.web.api.espn.com/apis/common/v3/sports/{sport}/{league}/athletes/{id}/...`. Works for NFL/NBA/NHL/MLB; **soccer is limited** (stats and gamelog return 404/400; use core API athlete endpoints instead).

Provider ids documented for odds (verify provider names in the response itself): Caesars 38, FanDuel 37, DraftKings 41, BetMGM 58, ESPN BET 68, Bet365 2000.

Useful parameters: `dates`, `week`, `seasontype` (1 pre, 2 regular, 3 post, 4 off), `season`, `limit`, `page`, `groups`, `lang`, `region`, `tz`.

Response shape (scoreboard): `events[]` each with `id`, `date` (UTC), `name`, `shortName`, `status.type.state` (`pre`/`in`/`post`), and `competitions[0].competitors[]` with `homeAway`, `team.displayName`, `score`, `records`. For core `odds`: `items[]` with `provider`, `details`, `overUnder`, `spread`, `homeTeamOdds`/`awayTeamOdds` (`moneyLine`, `favorite`).

## 4. Sport and league slugs

Path is `{sport}/{league}`.

- Soccer (`soccer`): `eng.1` Premier League, `eng.2` Championship, `eng.fa` FA Cup, `eng.league_cup`, `esp.1` LaLiga, `ger.1` Bundesliga, `ita.1` Serie A, `fra.1` Ligue 1, `ned.1` Eredivisie, `por.1` Primeira Liga, `sco.1` Scottish Premiership, `tur.1`, `usa.1` MLS, `mex.1` Liga MX, `bra.1`, `arg.1`, `ksa.1` Saudi Pro League, `nga.1` Nigerian Professional League, `gha.1`, `rsa.1`, `uefa.champions`, `uefa.europa`, `uefa.europa.conf`, `uefa.nations`, `caf.champions`, `caf.confed`, `caf.nations`, `conmebol.libertadores`, `fifa.world`, `fifa.worldq.caf` and the other `fifa.worldq.*`, `fifa.friendly`, `club.friendly`. Full list: https://github.com/pseudo-r/Public-ESPN-API/blob/main/docs/sports/soccer.md
- Basketball: `basketball/nba`, `wnba`, `mens-college-basketball`, `womens-college-basketball`, `nbl`, `fiba`
- American football: `football/nfl`, `college-football`, `cfl`, `ufl`
- Baseball: `baseball/mlb`, `college-baseball`, `world-baseball-classic`
- Hockey: `hockey/nhl`, `mens-college-hockey`
- Tennis: `tennis/atp`, `tennis/wta`
- Golf: `golf/pga`, `lpga`, `eur`, `liv`
- Racing: `racing/f1`, `irl`, `nascar-premier`
- MMA: `mma/{promotion}` (25+ promotions; list via the MMA doc)
- Also documented: cricket (numeric league ids via the header endpoint), rugby (24 leagues), rugby league, lacrosse, volleyball, water polo, field hockey, Australian football.

To discover slugs for a sport: `GET https://sports.core.api.espn.com/v2/sports/{sport}/leagues`.

## 5. Gotchas (from the community docs)

- Standings: `/apis/v2/`, not `/apis/site/v2/`.
- Some core responses contain `$ref` links on `sports.core.api.espn.pvt`; replace `.pvt` with `.com` to follow them.
- Season start/end from the calendar endpoint may not match when scoreboard data actually exists; if a scoreboard is empty, try a date range near the real match dates.
- Scoreboards truncate for NCAA sports without `groups=50&limit=500`.
- Event `date` is UTC; convert before telling the user a kickoff time.
- `competitions[0].id` normally equals the event id; if the odds URL 404s, read the competition id from the event.
- Missing data is common for lower leagues (no odds, no injuries, no predictor). Treat empty as "not available", never as "no injuries" or "no odds".

## 6. Rate-limit etiquette

- Probe once. Then fetch only what the review needs.
- Run calls sequentially or in small batches (a few at a time), not in a burst.
- Cache within the conversation: do not re-fetch the same URL.
- Retry at most twice on 429/5xx/timeout with exponential backoff (about 2 s, then 6 s) and honour `Retry-After` if present. A 403 or a block page is not retried.
- After the retries fail, switch down the ladder for the rest of the session rather than probing again on every step. `scripts/espn_fetch.py` does this bookkeeping and exits with code 3 and `{"status":"fallback", ...}` when you should switch.
- The docs ask users to follow ESPN's terms of service; this is for personal research, not redistribution or bulk scraping.

## 7. Fallback procedure (search/fetch/other tools)

For discovery, search for the fixtures page of each league on the date, using short queries: `{league} fixtures today {date}`, `{sport} schedule {date}`, `{league} matchday {n} fixtures`. Prefer the league's official site, then ESPN's scoreboard page, BBC/Sky/major outlets, then a livescore site. Confirm each kickoff time with at least two sources and convert to the user's timezone. Note postponed or rescheduled games. Use a connected sports-data tool first if one exists.

For per-leg research, ESPN data is only a starting point; the full research protocol in SKILL.md (official team news, injury reports, statistics providers) applies in every mode.

## 8. What ESPN data is good for

- Good: fixtures, kickoff times, status, league tables, team ids, recent results, rough injury leads, news headlines, ESPN's own win-probability or predictor outputs where present.
- Use with care: ESPN odds come from a handful of providers (US-oriented list above) and may not match the user's bookmaker or market. Treat them as a cross-check of how a market is priced, never as the odds on the user's ticket.
- Not enough on their own: injury and lineup confirmation (verify with the club or an official report and cite it), advanced statistics (expected goals and similar come from specialist providers), settlement rules (come from the bookmaker).
