# RAG Document Auditor

RAG Document Auditor is a locally runnable, evidence-first workspace for auditing document collections. It is designed for contradictions, duplicate or inconsistent content, ambiguous language, terminology variance, potentially outdated or broken references, important clauses, version comparison, cited Q&A, and downloadable audit reports.

It is not a generic “chat with PDF” application: the audit engine applies deterministic evidence checks before producing stored findings. Every displayed finding includes exact source chunks, and uncertainties are stated as review prompts.

> **Important:** This is AI-assisted analysis, not legal, financial, medical, compliance, or other professional advice. Verify all conclusions against the original documents and authoritative sources.

## Quick start

The full stack uses Docker (PostgreSQL, Qdrant, FastAPI, and Next.js):

```powershell
Copy-Item .env.example .env
# Set JWT_SECRET to a long random value and choose LLM_MODE=mock or ollama.
docker compose up --build
```

Open [http://localhost:3000](http://localhost:3000), create an account, create a workspace, then upload supported files.

For a fully local demo without Ollama, set `LLM_MODE=mock` and run:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Optional (recommended for semantic retrieval): pip install -r requirements-ml.txt
$env:EMBEDDING_PROVIDER = "hashing" # no model download; Sentence Transformers remains the production default
$env:LLM_MODE = "mock"
uvicorn app.main:app --reload
python scripts/load_demo.py
```

The demo documents are synthetic and deliberately include remote-work version changes, terminology variance, ambiguous qualifiers, a broken section reference, duplicate-like leave wording, and an old policy reference.

## Architecture

```text
Next.js + TypeScript UI
          │ REST / JWT
       FastAPI
  ┌───────┼───────────┐
PostgreSQL  local files  Qdrant
  metadata      │          vectors
          extraction → section-aware chunking → local embeddings
                                       │
                             audit rules / retrieval / Ollama
```

Documents are validated by extension, MIME-independent content limits, filename normalization, checksum de-duplication, workspace authorization, and safe generated storage names. PDF page numbers and document headings are preserved where available. Processing moves through `UPLOADING → PROCESSING → INDEXING → READY` and failures return understandable user-facing errors.

## RAG pipeline

1. A user question is embedded locally.
2. Qdrant searches only chunks with the active `workspace_id` payload filter.
3. The API rehydrates stored chunks and builds labeled context.
4. Ollama receives only retrieved context and is instructed to answer from evidence or state insufficiency.
5. Returned answers link to chunk citations. In `LLM_MODE=mock`, a deterministic source-only summarizer supports reliable tests and local offline checks.

`EMBEDDING_PROVIDER=local` uses Sentence Transformers (`all-MiniLM-L6-v2` by default). If its model cannot load, a deterministic hashing embedding fallback keeps local development functional, with lower semantic quality. Use Qdrant in production; the app falls back to a process-local vector store only when Qdrant is not configured.

## Audit engine

The modular engine lives in `backend/app/auditing/`:

- `contradiction_detector.py`: checks divergent numeric limits on related policy topics and marks them as potential conflicts.
- `duplicate_detector.py`: compares substantive term overlap across non-adjacent sections.
- `terminology_detector.py`: looks for known concept families such as Employee ID / Staff ID and prompts for contextual review.
- `ambiguity_detector.py`: identifies qualifiers such as “soon,” “reasonable time,” and “as necessary.”
- `reference_detector.py`: validates numbered section references against observed headings and calls old policy-version dates “potentially outdated.”
- `missing_info_detector.py`: cautiously reports incomplete approval workflows only where corpus-wide supporting details are absent.
- `clause_detector.py`: creates INFO-level review observations for obligations, restrictions, deadlines, exceptions, and responsibilities.

The `AI Audit Health Score` starts at 100 and subtracts severity penalties weighted by confidence (critical 18, high 10, medium 5, low 2, info 1). It is a transparent review prioritization heuristic, not an objective legal/compliance score.

## Main features

- Password-hashed registration/login and JWT-protected, workspace-isolated routes
- PDF, DOCX, TXT, Markdown extraction with error handling and page-aware metadata
- Heading/paragraph-aware chunking with sentence boundaries and overlap
- Local embedding provider abstraction and Qdrant filtering/insertion/search/deletion
- Async ingestion/audit jobs with actual status/progress stages
- Evidence-backed audit findings, status workflow, filters, source viewer, audit history
- Semantic token-based two-column document comparison
- Source-grounded chat, PDF/JSON report export, structured JSON logging
- Responsive accessible Next.js dashboard and synthetic demo data

## Configuration

Copy `.env.example` and set:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | PostgreSQL URL (SQLite is used by default for direct local runs) |
| `QDRANT_URL` | Qdrant URL; Docker provides `http://qdrant:6333` |
| `OLLAMA_BASE_URL`, `OLLAMA_MODEL` | Local Ollama endpoint/model |
| `LLM_MODE` | `ollama` for actual local inference; `mock` only for deterministic tests/demo |
| `EMBEDDING_MODEL`, `EMBEDDING_PROVIDER` | Sentence Transformer model / `hashing` offline fallback |
| `JWT_SECRET` | Required long random secret in production |
| `UPLOAD_DIR`, `MAX_FILE_SIZE_MB`, `CORS_ORIGINS` | Storage and security limits |

For Ollama, install it on the host, run `ollama pull llama3.2:3b`, set `LLM_MODE=ollama`, then start the stack. The app returns a clear setup message if Ollama cannot be reached.

## API

Interactive OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs).

Key routes include `POST /api/auth/register`, `POST /api/auth/login`, `GET|POST /api/workspaces`, `POST /api/workspaces/{id}/documents`, `POST /api/workspaces/{id}/audit`, `GET /api/workspaces/{id}/findings`, `PATCH /api/findings/{id}`, `POST /api/chat`, `POST /api/compare`, and `/api/audits/{id}/report.{pdf,json}`. All workspace data endpoints require `Authorization: Bearer <token>`.

## Tests

```powershell
cd backend
pytest -q
cd ..\frontend
npm install
npm run build
```

Backend tests cover extraction, heading-aware chunking, evidence-backed audit rules, registration, upload/processing, audit generation, citations, and chat in mock mode. Frontend type/build validation is performed by Next.js.

## Structure

```text
backend/app/
  auditing/       independent evidence detectors and scoring
  ingestion/      extraction, cleaning, chunking, processing
  rag/            embeddings, Qdrant store, retrieval, LLM, pipeline
  main.py         FastAPI API, auth-protected routes
frontend/app/     Next.js routes
frontend/components/ auditor dashboard and workflow UI
demo_data/        synthetic audit scenario
docker-compose.yml
```

## Security, privacy, and limitations

Passwords are Argon2-hashed; filenames are normalized; uploads are size/type/checksum checked; routes enforce workspace membership; and the frontend never renders backend filesystem paths. The intended deployment can keep files, embeddings, vectors, database, and Ollama inference local.

Current limitations: the comparison engine is a compact semantic token matcher; DOCX does not preserve Word page numbers; audits run in FastAPI background tasks (use a durable worker such as Celery/RQ for multi-instance deployments); and quality depends on extracted text and the chosen local models. The modular providers/detectors are intentionally structured to support those upgrades without rewriting the product.
