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
- [x] git repo initialized, pushed to private GitHub repo `orub`

## Phase 2 — Discogs ingestion pipeline (design doc §4.2, §8) — fetch-by-id slice DONE 2026-08-29

Scoped down (user's choice) to "fetch a single release by id" for this
iteration, deferring search/disambiguation and full collection sync.

- [x] Discogs API token / auth setup — `.env` (gitignored) + `.env.example`
      (blank placeholder) + `src/orub/config.py` (`Settings`, pydantic-settings)
- [x] Pydantic DTOs for raw Discogs JSON → mapping into domain types
      — `src/orub/discogs/models.py` (DTOs), `src/orub/discogs/mapping.py`
      (pure `release_from_dto`, unsupported/missing format & label → `Err`)
- [x] Discogs HTTP client — `src/orub/discogs/client.py` — 404 → `Ok(None)`,
      429 → `Err(RateLimited)`, other 4xx/5xx → `Err(NetworkError)`,
      connection failure → `Err(NetworkError)`, bad shape → `Err(MalformedResponse)`
- [x] Rate limit handling — reactive (surface 429 as `Err(RateLimited)`);
      proactive throttling deferred until bulk operations (full collection sync)
- [x] `ingest_release_by_id` orchestration — `src/orub/discogs/ingest.py` —
      pure function, `fetch_release`/`existing_release` injected as callables
      (user's choice: inject a lookup function rather than build persistence
      now); produces `Created` / `AlreadyExists` / `NotFound`
- [x] pytest suite (respx-mocked, no real network) — client, mapping, ingest
      orchestration, config — 100% coverage
- [x] Verified end-to-end against the real Discogs API (release 249504 and a
      bogus id) — DTO/mapping assumptions match live responses
- [x] Discogs search: `DiscogsClient.search_releases(release_title=, track_title=,
      artist=, label=, year=)` against `/database/search` — a distinct, thinner
      DTO shape than release detail (`DiscogsSearchResultDTO`/`DiscogsSearchResponseDTO`
      in `models.py`: id, title as combined "Artist - Title", year, country,
      denormalized label/format name lists, catno). No results → `Ok(())`, not
      an error. Verified against the real API (release-title+artist+label+year,
      track-title search, and a no-match query).
- [x] Wire search into `ingest.py`: `ingest_release_by_search` — search →
      candidates → `AmbiguousMatch` when >1 match, `NotFound` on none, unique
      match flows into existing `ingest_release_by_id` to fetch + ingest the
      full release (never maps search results directly into a `Release`)
- [x] CLI command to exercise search-based ingestion — `orub search-release
      [--release-title] [--track-title] [--artist] [--label] [--year]`,
      lists candidates with `[id=...]` on an ambiguous match. Verified live
      against the real API: unique match → `Created` (Squarepusher - Feed Me
      Weird Things, id=52382), ambiguous match (Rick Astley - Never Gonna
      Give You Up, 50+ candidates), and no-match query.
- [ ] Deduplication rules (not built — `existing_release` is currently a
      stand-in that always returns "no match" since there's no persistence
      layer yet; see Phase 3)
- [ ] Pagination for search results (currently only the first page/50 results
      is fetched; fine for now, revisit if it matters in practice)

## Phase 3 — Persistence layer (design doc §4.3, §5, §8)

First slice DONE 2026-08-30 (user's choice): catalog side only (`Release`/
`Track`), dedup by Discogs release id via a real `existing_release` lookup
— the natural key, and it makes `AlreadyExists` reachable for the first
time. `CollectionItem`/`Tag`/`Edge`/user-scoping deferred to a later slice
since they need users/auth to mean anything yet.

- [x] SQLAlchemy schema for the catalog slice — `src/orub/db/models.py`:
      `ReleaseRow`, `TrackRow`, `TrackArtistRow`. No `artists`/`labels`
      tables yet: `orub.discogs.mapping` never actually produces `Artist`/
      `Label` domain objects with names, only bare ids referenced from
      `Release`/`Track` — a table with just an id column would be pure
      ceremony. `label_id`/`artist_id` are plain int columns for now;
      flagged for confirmation, revisit once ingestion captures names.
- [x] Explicit mapping functions ORM ↔ domain types (no ORM leakage) —
      `src/orub/db/mapping.py` (`release_to_row`/`release_from_row`)
- [ ] `user_id` scoping on every user-owned table — N/A for this slice,
      revisit with the `CollectionItem`/`Tag`/`Edge` slice
- [ ] Scoped-repository pattern (single place that appends `WHERE user_id = ...`)
      — same, N/A until user-owned tables exist
- [x] SQLite for local dev, sync SQLAlchemy (no async needed yet) —
      `Settings.database_url` (default `sqlite:///orub.db`), `src/orub/db/
      session.py`. Neon Postgres is the Phase 8 deploy target, swapped in
      via the same engine URL.
- [x] `src/orub/cli.py` wired to real persistence: `existing_release` is a
      DB lookup (`src/orub/db/repository.py`), and a `Created` outcome is
      saved before being reported, for both `ingest-release` and
      `search-release`. Live-validated against the real Discogs API
      (Squarepusher - Feed Me Weird Things, id=52382): first run →
      `Created` + release/12 tracks persisted, second run → `Already
      exists`.
- [ ] Alembic deferred until the schema stabilizes (use
      `Base.metadata.create_all()` for now) — add Alembic migration setup
      right before Phase 8 deploy, once catalog + user-specific schema are
      both settled, rather than migrating a schema still in flux
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

- [x] typer command surface: `orub ingest-release <id>` (fetch by id, report
      `Created`/`AlreadyExists`/`NotFound`/error) — `src/orub/cli.py`, wired
      as the `orub` console script in `pyproject.toml`. `rebuild-graph`,
      `suggest` etc. wait on Phase 4/3.
- [x] Commands wrap domain/ingestion/graph functions directly (no API
      dependency) — `ingest-release` calls `ingest_release_by_id` directly

## Phase 7 — Elm frontend (design doc §4.7, §8)

- [ ] Page/model structure
- [ ] JSON decoders/encoders matching the API contract
- [ ] Decide hand-written vs. generated client code
- [x] Server-side OCR for the catno scan control (2026-09-02): `src/orub/ocr/`
      (`extract.py` impure tesseract call returning `Result[str, OcrError]`,
      `parse.py` pure whitespace cleanup — same pure-core/impure-edge split as
      `discogs/`), `POST /ocr/scan` (multipart upload, returns
      `{catno, raw_text}`). Assumes a clean close-up shot of just the catno
      (user's framing choice) rather than parsing a full noisy label photo.
      Elm: `Page/Search.elm`'s scan button now uploads the captured `File` via
      `Http.filePart` instead of the old capture→Submit bypass, and fills the
      `catno` field when found (still user-editable/reviewable before
      search); `raw_text` is shown on no-match so OCR quality can be eyeballed
      against real photos. No camera-overlay/guide-box UI (would need
      `getUserMedia` + `<video>` + canvas instead of the current native-camera
      `<input capture>`, a bigger rewire — deferred, user's call, revisit only
      if plain photos prove hard to frame in practice).

## Phase 8 — Deployment (design doc §7, §8)

- [ ] Neon Postgres project
- [ ] Render (or Railway) backend service
- [ ] Static hosting for compiled Elm (Render static / Cloudflare Pages / Netlify)
- [ ] Env var / secrets management
- [ ] CI/CD: build Elm, run backend tests, deploy on push
- [ ] Alembic migration execution strategy in deploy pipeline
- [ ] Logging/monitoring within free-tier constraints
- [ ] Backup/export plan for user data
