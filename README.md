# DocuLens

DocuLens is an agentic document-intelligence platform for producing structured,
traceable analysis and evidence-grounded answers from complex documents.

The repository includes the implemented MVP path for document analysis and grounded
Q&A. Its deterministic evaluation harness and measured baseline limitations are in
[`docs/evaluation.md`](docs/evaluation.md).

## Repository layout

- `apps/web` — Next.js user interface
- `apps/api` — FastAPI application and persistence boundary
- `agent` — LangGraph orchestration and document-specific extractors
- `ingestion` — document parsing and structure detection
- `retrieval` — chunking, search, reranking, and citations
- `evals` — evaluation datasets and runners
- `tests` — unit, integration, and test fixtures
- `docs` — architecture and decision records

See [`doculens_idea.md`](doculens_idea.md) for the product and architecture brief.

## Local development (Docker Compose)

Prerequisites: Docker Engine with the Compose plugin (`docker compose version`).

1. Copy the example environment file and adjust values if needed. The
   defaults are safe for local use only.

   ```sh
   cp .env.example .env
   ```

2. Build and start the API and PostgreSQL/pgvector services in the
   background:

   ```sh
   docker compose up -d --build
   ```

3. Check service status and health:

   ```sh
   docker compose ps
   docker compose logs -f api
   ```

4. Apply database migrations (not run automatically at container start):

   ```sh
   docker compose exec api alembic -c apps/api/alembic.ini upgrade head
   ```

5. Call the health endpoint from the host (default port `8000`, or whatever
   `API_HOST_PORT` is set to in `.env`):

   ```sh
   curl --fail http://localhost:8000/health
   ```

6. Create and retrieve a document:

   ```sh
   curl --fail -X POST http://localhost:8000/api/documents \
     -F "file=@/path/to/file.pdf;type=application/pdf"
   curl --fail http://localhost:8000/api/documents/<id-from-the-response>
   ```

7. Stop the stack without losing database data:

   ```sh
   docker compose down
   ```

   Data persists in the named volume `doculens_pgdata` and is restored the
   next time you run `docker compose up -d` (migrations do not need to be
   reapplied unless the schema changed).

8. To intentionally delete the local database and start from empty data,
   remove the volume as well (destructive — this cannot be undone):

   ```sh
   docker compose down -v
   ```

### Running migrations outside Compose

Against any database reachable via `DATABASE_URL` (see `.env.example`):

```sh
alembic -c apps/api/alembic.ini upgrade head
alembic -c apps/api/alembic.ini downgrade base
```

Notes:

- The database port is not published to the host by default.
- `POST /api/documents/parse` remains a stateless, database-free parse — it
  works even when PostgreSQL is unavailable.

## Local development (frontend)

Prerequisites: the API running locally (see above), and Node.js 24+.

1. Copy the example environment file:

   ```sh
   cp apps/web/.env.example apps/web/.env.local
   ```

2. Install dependencies and start the dev server:

   ```sh
   cd apps/web
   npm install
   npm run dev
   ```

3. Open `http://localhost:3000`, upload a PDF, and you'll be taken to its
   document page. The frontend calls the API through a same-origin Next.js
   route handler, so no backend CORS configuration is needed.

Frontend checks:

```sh
cd apps/web
npm run lint
npm run typecheck
npm run test
npm run build
```

## Precomputed demos

After applying migrations, seed the three original synthetic demos explicitly:

```sh
python -m app.demo.seed
```

The command is transactional and idempotent, makes no provider/network calls, and
fails rather than overwriting a mismatched fixture. In Compose use
`docker compose exec api python -m app.demo.seed`. Demo analysis and curated answers
are visibly labeled precomputed.

## Anonymous public quotas

Local development is unmetered by default (`PUBLIC_DEMO_MODE=false`). For a public
deployment, set `PUBLIC_DEMO_MODE=true` and configure the same unique 32-byte-or-longer
`ANONYMOUS_SESSION_SECRET` on the API and web services. Defaults allow three new
analyses and three new indexes per UTC day per signed anonymous session, plus ten
provider-backed questions per document for that session. Cache hits and curated demo
reads are free. Cookie-based quotas are cost controls, not strong identity or complete
abuse prevention; edge-level burst protection remains a deployment responsibility.
