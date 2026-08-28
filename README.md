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
