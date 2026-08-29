# DocuLens

DocuLens is an agentic document-intelligence platform for producing structured,
traceable analysis and evidence-grounded answers from complex documents.

The repository is currently an architecture-only bootstrap. Product behavior
and local-development instructions will be added as implementation begins.

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

4. Call the health endpoint from the host (default port `8000`, or whatever
   `API_HOST_PORT` is set to in `.env`):

   ```sh
   curl --fail http://localhost:8000/health
   ```

5. Stop the stack without losing database data:

   ```sh
   docker compose down
   ```

   Data persists in the named volume `doculens_pgdata` and is restored the
   next time you run `docker compose up -d`.

6. To intentionally delete the local database and start from empty data,
   remove the volume as well (destructive — this cannot be undone):

   ```sh
   docker compose down -v
   ```

Notes:

- The PostgreSQL/pgvector connection variables (`POSTGRES_DB`,
  `POSTGRES_USER`, `POSTGRES_PASSWORD`) are provided to the `api` container
  ahead of the persistence integration slice; no current API code reads them.
- The database port is not published to the host by default.
