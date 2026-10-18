# Hindsight Frontend

The modern Next.js frontend for **Hindsight — The Autonomous SRE Crew with Live Operational Graph Memory**.

It hosts:
- `/` — A cinematic, liquid-glass marketing landing page detailing Hindsight's autonomous operational graph memory, zero-mutex crew coordination, and the stale-memory trap.
- `/app` — The real-time War Room UI featuring Cytoscape interactive topology canvas, autonomous crew lanes, Why drawer, graph toggle, time scrubber, race harness, and approval gate.

---

## Running Locally

### Development Mode

Ensure the backend services are running (or running via Docker Compose at `http://localhost:8000`).

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) for the landing page or [http://localhost:3000/app](http://localhost:3000/app) for the War Room.

In development, requests to `/api/*`, `/mcp`, and `/health` are automatically proxied to `http://localhost:8000` via Next.js rewrites.

### Production Static Export

```bash
npm run build
```

This compiles a static export to `frontend/out/` (`output: 'export'`, `trailingSlash: true`). The FastAPI backend mounts and serves `out/index.html` at `/` and `out/app/index.html` at `/app`.

---

## How Media Works & How to Swap Videos

All video and fallback poster references are defined centrally in:
`src/lib/media.ts`

```ts
export const media = {
  hero: {
    poster: '/images/hero-bg.jpg',
    video: 'https://d8j0ntlcm91z4.cloudfront.net/...',
  },
  // ...
};
```

### Swapping External Videos with Local MP4s

To replace the external CloudFront demonstration videos with your own local MP4 videos:

1. Place your `.mp4` video files into `frontend/public/videos/`:
   - e.g. `frontend/public/videos/hero.mp4`
   - e.g. `frontend/public/videos/featured.mp4`
   - e.g. `frontend/public/videos/philosophy.mp4`
   - e.g. `frontend/public/videos/service-graph.mp4`
   - e.g. `frontend/public/videos/service-crew.mp4`

2. Open `src/lib/media.ts` and update the `video` property:
   ```ts
   hero: {
     poster: '/images/hero-bg.jpg',
     video: '/videos/hero.mp4',
   }
   ```

3. To disable video and show the generated poster image exclusively, set `video: null`.

**No other code changes are required.** The `MediaBlock` and `HeroBackground` components handle video streaming, looping, seamless crossfades, error handling, and poster fallbacks automatically.
