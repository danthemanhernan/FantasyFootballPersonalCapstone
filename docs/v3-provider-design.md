# V3 provider design: ESPN first

## Goal

Load a canonical fantasy roster without allowing ESPN-specific payloads,
identifiers, or failure semantics to leak into the HUD and scoring domain.
The first provider is ESPN Fantasy Football, but the port is intentionally
provider-neutral so a second provider can be added without rewriting the app.

## ESPN constraints

ESPN Fantasy exposes an undocumented API surface commonly used at endpoints
under `fantasy.espn.com/apis/v3/games/ffl/...` or the read host
`lm-api-reads.fantasy.espn.com`. Private-league access generally depends on
the signed-in browser session, including the `SWID` and `espn_s2` cookies.
Those details are integration concerns, not domain data, and no cookie values
belong in source control, localStorage snapshots, or test fixtures.

The first increment therefore uses a credential-free fixture adapter and an
HTTP client with an injected `fetch` function. Live authentication is a
separate boundary decision once the fixture contract is stable.

## Observed ESPN shape check

Public community documentation and unofficial OpenAPI descriptions agree on
the shape used by the current adapter:

```text
GET /apis/v3/games/ffl/seasons/{season}/segments/0/leagues/{leagueId}
    ?view=mTeam&view=mRoster&scoringPeriodId={period}

response.teams[].roster.entries[] {
  playerId,
  lineupSlotId,
  playerPoolEntry: {
    id,
    player: { id, fullName, defaultPositionId, proTeamId }
  }
}
```

The mapper consumes the nested player identity and display fields, while the
optional scoring period is carried in `LeagueRef`. The fixture includes the
extra roster fields so tests resemble the observed response without coupling
the canonical model to lineup or acquisition details. These are observed,
community-maintained descriptions of an undocumented API, not an ESPN-published
stability guarantee.

## Ports and models

```text
ProviderPort.loadRoster(LeagueRef) -> CanonicalRoster | ProviderError

ESPN DTO -> validate -> ESPN mapper -> CanonicalRoster -> HUD/scoring
```

The canonical roster contains only the fields the product currently needs:
provider-neutral player ID, display name, position, team, and provider source
metadata. ESPN player IDs and team IDs are retained only as opaque source
identifiers for traceability.

## Failure policy

- `401`/`403`: `AUTHENTICATION_REQUIRED`; do not retry automatically.
- `404`: `NOT_FOUND`; do not retry automatically.
- `429`: `RATE_LIMITED`; retry only after a future caller-owned backoff policy.
- `5xx`, network errors, and timeouts: `UNAVAILABLE`; bounded retry belongs in
  the ingestion/application layer, not inside the mapper.
- Invalid JSON or a renamed/missing field: `INVALID_PAYLOAD`; do not retry.

The adapter returns classified errors rather than throwing provider-specific
strings. Tests inject every failure without contacting ESPN. A caller-owned
`loadRosterWithRetry` wrapper retries only `UNAVAILABLE`, with a bounded number
of attempts; authentication, not-found, rate-limit, and payload errors remain
terminal. This keeps retry policy out of the DTO mapper and makes it possible
to test backoff without waiting on real time.

## Implemented boundary

```text
ESPN JSON --(shape validation)--> ESPN mapper --(canonical roster)--> ProviderPort consumer
     |                                  |
 HTTP status / timeout             ProviderError
```

The fixture adapter uses the same mapper as the HTTP client, so offline tests
exercise the real translation path. The mapper rejects malformed nested teams
and player records before any ESPN-shaped value can reach the rest of the app.

## Deliberate deferrals

This milestone does not claim production ESPN authentication, automatic
refresh, rate-limit backoff, pagination, or a provider-approved API contract.
The browser extension has host permissions, but private-cookie handling and
ESPN terms/security implications must be settled before enabling live access.
