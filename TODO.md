# TODO

Checklists tracking implementation against `vinyl-helper-design-doc.md`. Keep
this updated as work lands — check items off in the same change that
completes them, add new items when scope becomes clearer, don't let it drift.

Working style (see design doc §2 and project `AGENTS.md`): one small piece at
a time, tested green, before moving to the next. Don't build ahead of what's
been asked for.

## Phase 1 — Domain core (design doc §3, §4.1) — DONE 2026-08-29

- [x] Project scaffold: uv-managed pyproject, Makefile, ruff/pyright config
- [x] `Result[T, E]` (`Ok` / `Err`) — design doc §2 — `src/orub/domain/result.py`
- [x] Identity types: `ArtistId`, `LabelId`, `ReleaseId`, `TrackId` — §3 Identity
      — `src/orub/domain/identity.py`. Also added `UserId`, `TagCategoryId`,
      `TagId` here (not named in §3, but needed by §3 User-specific entities;
      flagged for confirmation).
- [x] Closed sum types — §3 Closed sum types — `src/orub/domain/sums.py`,
      `src/orub/domain/ingest_outcome.py`
  - [x] `EdgeSource` (Auto | Manual)
  - [x] `RecordFormat` (Vinyl, CD, Cassette — grow as ingestion work discovers
        more Discogs format strings)
  - [x] `MusicalKey` (Camelot notation, 24 members)
  - [x] `Bpm` value type
  - [x] `Condition` (Discogs grading scale) — not explicitly named as a
        closed sum type in §3, but added since CollectionItem.condition is
        clearly a fixed vocabulary too; flagged for confirmation.
  - [x] `IngestOutcome` (Created | AlreadyExists | AmbiguousMatch | NotFound),
        generic over the created entity type and candidate type — filled in
        concretely by Phase 2
- [x] Catalog entities — §3 Catalog entities — `src/orub/domain/catalog.py`
  - [x] `Artist`, `Label` (referenced by id elsewhere, not embedded)
  - [x] `Release` (`label_id` reference; `tracklist: tuple[Track, ...]` embedded
        since tracks don't exist independently of their release — a judgment
        call, doc left this open; flagged for confirmation)
  - [x] `Track` (optional `bpm`, `key`; `artist_ids` reference, not embedded)
- [x] User-specific entities — §3 User-specific entities — `src/orub/domain/user.py`
  - [x] `CollectionItem` (`tag_ids: frozenset[TagId]` for arbitrary-cardinality tags)
  - [x] `Tag` / `TagCategory`
  - [x] `Edge` (fields named `from_track_id`/`to_track_id` since `from` is a
        Python keyword)
- [x] pytest suite for domain types (immutability, equality, exhaustive
      `match` over sum types) — 36 tests, 100% coverage
- [x] `hypothesis` wired in as a dev dependency (property tests land with the
      compatibility-scoring function in Phase 4, not before)
- [x] `ruff check` / `ruff format` / `pyright --strict` / `pytest` all green
- [ ] git repo initialized, pushed to private GitHub repo `orub`

## Phase 2 — Discogs ingestion pipeline (design doc §4.2, §8)

- [ ] Decide search/matching strategy against Discogs API
- [ ] Deduplication rules
- [ ] Pydantic DTOs for raw Discogs JSON → mapping into domain types
- [ ] `AmbiguousMatch` resolution flow (how the user disambiguates)
- [ ] Rate limit handling
- [ ] Discogs API token / auth setup (deferred by user request as of
      2026-08-29 — revisit before starting this phase)

## Phase 3 — Persistence layer (design doc §4.3, §5, §8)

- [ ] SQLAlchemy schema: tables + indexes for catalog + user-specific entities
- [ ] Explicit mapping functions ORM ↔ domain types (no ORM leakage)
- [ ] `user_id` scoping on every user-owned table
- [ ] Scoped-repository pattern (single place that appends `WHERE user_id = ...`)
- [ ] Alembic migration setup + workflow
- [ ] (optional) Postgres row-level security as second isolation layer

## Phase 4 — Graph module (design doc §4.4, §8)

- [ ] Camelot-wheel + BPM compatibility scoring (pure functions)
- [ ] hypothesis property tests (symmetry, same-key maximal compatibility, etc.)
- [ ] `EdgeGraph` typed wrapper over networkx
- [ ] Auto vs. Manual edge interaction/override/delete semantics
- [ ] Edge weighting + "suggest next track" query design

## Phase 5 — API layer (design doc §4.5, §8)

- [ ] Full endpoint list
- [ ] FastAPI dependency injection for user-scoping
- [ ] Request/response pydantic models
- [ ] Error response shapes
- [ ] Auth: password hashing scheme, session vs. JWT, registration/login,
      token/session expiry

## Phase 6 — CLI (design doc §4.6, §8)

- [ ] typer command surface (e.g. `ingest`, `rebuild-graph`, `suggest`)
- [ ] Commands wrap domain/ingestion/graph functions directly (no API dependency)

## Phase 7 — Elm frontend (design doc §4.7, §8)

- [ ] Page/model structure
- [ ] JSON decoders/encoders matching the API contract
- [ ] Decide hand-written vs. generated client code

## Phase 8 — Deployment (design doc §7, §8)

- [ ] Neon Postgres project
- [ ] Render (or Railway) backend service
- [ ] Static hosting for compiled Elm (Render static / Cloudflare Pages / Netlify)
- [ ] Env var / secrets management
- [ ] CI/CD: build Elm, run backend tests, deploy on push
- [ ] Alembic migration execution strategy in deploy pipeline
- [ ] Logging/monitoring within free-tier constraints
- [ ] Backup/export plan for user data
