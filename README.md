# orub

Personal vinyl collection tracker and track-compatibility graph tool. See
[`vinyl-helper-design-doc.md`](vinyl-helper-design-doc.md) for the design
and [`TODO.md`](TODO.md) for implementation progress against it.

## Development

```sh
make setup      # uv sync
make check      # lint + typecheck + test
```

## Testing on a phone

The Elm frontend has a camera-capture control (`Page/Search.elm`) meant to be
tried on an actual phone. `Api.elm` hardcodes `apiBaseUrl = "http://localhost:8000"`,
which only works when the browser and the API are on the same machine, so a
phone can't reach it as-is.

Two ways to get a phone talking to your laptop's dev servers, in order of
preference:

1. **Quick tunnel (recommended)** — sidesteps LAN/firewall issues entirely,
   since `cloudflared` makes an outbound connection that macOS's firewall
   doesn't block:

   ```sh
   uv run uvicorn orub.api.app:app --host 0.0.0.0 --port 8000
   (cd frontend && npx elm-live src/Main.elm --host 0.0.0.0 --port 5001 -- --output=main.js)
   cloudflared tunnel --url http://localhost:8000   # note the printed URL
   cloudflared tunnel --url http://localhost:5001   # note the printed URL
   ```

   Temporarily set `apiBaseUrl` in `frontend/src/Api.elm` to the backend
   tunnel URL, then open the frontend tunnel URL on the phone (any network —
   wifi or cellular). **Revert `apiBaseUrl` back to `localhost:8000` once
   you're done** — the tunnel URLs are random and short-lived anyway.

2. **Same-wifi LAN IP** — works without installing anything extra, but
   requires the phone and laptop on the same wifi *and* macOS's Application
   Firewall (System Settings → Network → Firewall) to allow incoming
   connections for the `python`/`node` processes running the dev servers
   (or the firewall temporarily disabled). Same server commands as above,
   but bind to the laptop's LAN IP (`ipconfig getifaddr en0`) instead of a
   tunnel URL, both in `Api.elm` and the phone's browser address.

There's no `.elm` flag/env-based base-URL switch yet (e.g. deriving it from
`window.location.hostname`) — this is a manual, temporary edit each time.
