# Vinyl Helper — Design Doc

## 1. Goal

A personal tool (max ~10 users) that lets someone look up their vinyl records on Discogs, store their collection, and build a graph of "this track can follow this track" — partly auto-generated from track compatibility, partly hand-curated by the user. Frontend is Elm; backend is Python. Design philosophy: push as much correctness as possible into the type system and function composition, Elm-style, rather than relying on runtime checks and exceptions.

## 2. Guiding principles

- Domain types are the source of truth. Core domain objects are attrs classes (frozen=True, slots=True) — immutable, cheap to compare, close to Elm records.
- Closed sums over open strings. Anything with a fixed set of variants (edge source, record format, ingest outcome, musical key) is an Enum/tagged union, never a bare string, so match statements can be exhaustive and mypy/pyright (strict mode) can catch missing cases.
- Result over exceptions for expected failure. A small hand-rolled Result[T, E] (Ok / Err as attrs classes) is used for anything that can fail in an expected way (ambiguous Discogs match, not found, validation failure). Exceptions are reserved for truly exceptional/programmer-error cases.
- Validation at the boundary only. pydantic is used only where untrusted data enters the system: Discogs API responses and FastAPI request/response bodies. Once validated, data is converted into the attrs domain types and pydantic disappears from the rest of the codebase.
- Pure core, impure edges. Domain logic (matching, compatibility scoring, graph construction) is pure functions over domain types. SQLAlchemy, the Discogs client, FastAPI, and networkx are all pushed to the edges, behind small typed interfaces, so the core is trivially unit-testable.
- Tooling: attrs for domain types, pydantic for boundary parsing, typer for a CLI to exercise ingestion/graph logic without the API, pytest + pytest-cov for tests, hypothesis for property-based tests (especially the Camelot/BPM compatibility logic).

## 3. Core domain model

### Identity

- ArtistId, LabelId, ReleaseId — sourced from Discogs' own IDs (Discogs is the source of truth for these entities).
- TrackId — minted by us, since Discogs does not give tracks stable IDs (they're positions like "A1", "B2" within a release). Likely (release_id, position) as a composite key, or a UUID if we want position changes to not break identity.

### Catalog entities (not user-specific)

- Artist — id, name, (profile data as needed).
- Label — id, name.
- Release — id, title, label, year, format, tracklist (list of Track).
- Track — id, release id, position, title, artist(s), and optional bpm: Bpm | None and key: MusicalKey | None — these are almost never present from Discogs and must be explicitly nullable, filled in later by the user or by audio analysis.

### User-specific entities

- CollectionItem — "this user owns this release": user id, release id, condition, notes, date added, plus:
  - Tags: user-defined, many-to-many. A tag belongs to a tag category (also user-defined) — e.g. category "Mood" with tags "Chill"/"Peak time", category "Occasion" with tags "Wedding"/"Warmup". Both tags and categories are per-user, arbitrary cardinality (a CollectionItem can have any number of tags across any number of categories).
- Edge — a directed "track A can follow track B" relationship: from TrackId, to TrackId, source: EdgeSource (Auto | Manual), optional weight/compatibility_score, created_at, owning user.

### Closed sum types

- EdgeSource = Auto | Manual
- RecordFormat — closed enum validated against what Discogs returns (Vinyl, CD, Cassette, ...).
- MusicalKey — represented directly in Camelot notation (or 12 pitch classes × major/minor, convertible to Camelot) to support harmonic-mixing compatibility scoring.
- IngestOutcome = Created | AlreadyExists | AmbiguousMatch(candidates) | NotFound — ingestion is modeled as producing one of these, not as an exception or a boolean.

## 4. Layering

1. Domain core (attrs types + pure functions) — no dependency on SQLAlchemy, FastAPI, or the Discogs client.
2. Discogs ingestion pipeline — raw JSON → pydantic DTOs (validated shape) → mapped into domain types, producing an IngestOutcome. Handles search, rate limiting, and match disambiguation.
3. Persistence layer — SQLAlchemy models are a separate representation from the domain types, with explicit mapping functions both ways (ORM never leaks into domain/business logic). Single shared Postgres database; every table scoped by user_id (see §5).
4. Graph module — edges are loaded from the DB into networkx behind a small typed interface (e.g. EdgeGraph wrapper); the Camelot-wheel/BPM compatibility scoring is pure functions over Track/MusicalKey/Bpm, independent of networkx or the DB.
5. API layer — FastAPI + pydantic request/response models; auth (email + password); every DB-touching endpoint goes through a user-scoping mechanism so it's structurally difficult to query another user's data.
6. CLI — typer commands wrapping the same domain/ingestion/graph functions, for testing and one-off operations without spinning up the API.
7. Elm frontend — talks to the FastAPI layer over a JSON contract that mirrors the API layer's pydantic models.

## 5. Data isolation

Decision: single shared Postgres database, not a database-per-user. Every user-owned table (collection_items, tags, tag_categories, edges) carries a user_id column. Isolation is enforced in code, not by physical separation — acceptable for a small, trusted user base (≤10 people), and it unlocks simple free-tier hosting (see §7). Mitigations to keep this safe: a single scoped-repository/dependency pattern that all queries go through (so there's one place that appends WHERE user_id = ..., not scattered throughout the codebase), and optionally Postgres row-level security as a second layer of defense.

## 6. Testing strategy

- pytest for unit and integration tests.
- pytest-cov for coverage tracking.
- hypothesis for property-based testing, especially on the Camelot-wheel/BPM compatibility function (pure, small closed input domain — ideal for property tests like "compatibility is symmetric" or "same key is always maximally compatible").
- Domain core and graph/compatibility logic should be testable with no DB or network access at all, by construction of the layering in §4.

## 7. Deployment plan

- Database: Neon (free tier Postgres). Chosen over Render's own free Postgres because Render's free Postgres expires and is deleted after 30 days; Neon's free tier has no such expiration (it scale-to-zeros when idle, which is fine for personal/low-traffic use), and 0.5GB storage is ample for 10 users' worth of collection metadata.
- Backend: Render free web service (or Railway) running FastAPI/Uvicorn, connecting to Neon over the network — no reliance on local disk, since all persistent state lives in Neon.
- Frontend: Elm compiled to static JS/HTML, hosted free as a static site (Render static site, Cloudflare Pages, or Netlify).
- Auth: local email + password, hashed credentials stored in the same Neon database, session cookie or JWT (TBD in the API design part).
- This combination requires no server administration (no VM, no manual TLS/nginx setup) and deploys on git push, at the cost of isolation being logical (user_id scoping) rather than physical (separate files) — an acceptable tradeoff already agreed for this project's scale.

## 8. What remains to be designed

- Discogs ingestion pipeline details: search/matching strategy, deduplication rules, how AmbiguousMatch is surfaced to and resolved by the user, Discogs API rate limit handling.
- SQLAlchemy schema & migrations: concrete table definitions, indexes, Alembic migration setup and workflow.
- Tag/tag-category data model: exact schema for user-defined tags and categories (many-to-many join tables), and how they surface in the API/UI.
- Graph/edges design details: the Camelot-wheel + BPM compatibility scoring function itself, how Auto and Manual edges interact or conflict (e.g. can a user override/delete an auto-generated edge?), edge weighting and how "suggest next track" queries work over the graph.
- API contract: full endpoint list, FastAPI dependency injection for user-scoping, request/response pydantic models, error response shapes.
- Auth flow specifics: password hashing scheme, session vs. JWT decision, registration/login endpoints, token/session expiry.
- CLI command surface: which typer commands exist (e.g. ingest, rebuild-graph, suggest), and how they map to domain functions.
- Elm frontend architecture: page/model structure, JSON decoders/encoders matching the API contract, how the two sides are kept in sync (hand-written vs. generated).
- Deployment mechanics: environment variable/secrets management, CI/CD (build Elm, run backend tests, deploy on push), Alembic migration execution strategy in the deploy pipeline, basic logging/monitoring within free-tier constraints, and a backup/export plan for user data given reliance on a free managed database.
