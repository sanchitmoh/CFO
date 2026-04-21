# AI Virtual CFO Platform

An AI-powered CFO-as-a-service that gives small businesses 24/7 access to financial insights, forecasting, and strategic guidance — at a fraction of the cost of hiring a full-time CFO.

## The Problem

Small businesses make up 33.3 million businesses in the US, yet most lack dedicated financial expertise. A full-time CFO costs $200K–$400K/year — unaffordable for most SMBs. Meanwhile, 44% of startups fail due to cash flow problems.

## The Solution

A cloud-based SaaS platform where SMB owners connect their bank and accounting data, then receive real-time insights, AI-driven forecasts, proactive alerts, and a conversational CFO assistant — all through a clean dashboard and chat interface.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Next.js 16 · React 19 · TypeScript | Server-side rendering, fast UI, type safety |
| **Styling** | Tailwind CSS v4 | Rapid professional UI with utility-first CSS |
| **Charts** | Recharts | Interactive financial charts and visualizations |
| **Auth** | Clerk (Next.js + JWT) | Secure authentication with multi-user role management |
| **Icons** | Lucide React | Consistent icon library across the UI |
| **Backend** | Python · FastAPI | High-performance async API server |
| **Database** | PostgreSQL (Neon) | Serverless Postgres for financial data |
| **Migrations** | Alembic | Version-controlled database schema management |
| **ORM** | SQLAlchemy 2.0 (async) | Async database access with type-safe models |
| **Caching** | Redis (Upstash) | Read-through cache for dashboard aggregations |
| **AI / Chat** | OpenAI GPT-4o | RAG-backed conversational CFO assistant |
| **Semantic Search** | pgvector + sentence-transformers | Vector embeddings for natural-language financial queries |
| **Banking** | Plaid API | Real-time bank account connection and transaction sync |
| **Encryption** | Fernet (cryptography) | Field-level encryption for webhooks and API keys |
| **Observability** | OpenTelemetry | Distributed tracing for FastAPI, SQLAlchemy, and HTTPX |

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Frontend (Next.js 16)                │
│  Clerk Auth · Dashboard · Chat · Forecasting · Alerts    │
│  Budgets · Goals · Reports · Calculator · Investor View  │
└────────────────────────┬─────────────────────────────────┘
                         │ REST API (JSON / SSE streaming)
┌────────────────────────▼─────────────────────────────────┐
│                    Backend (FastAPI)                      │
│  18 API Routers · OpenTelemetry · JWT Validation         │
├──────────┬───────────┬───────────┬───────────────────────┤
│ OpenAI   │  Plaid    │  Redis    │  PostgreSQL (Neon)    │
│ GPT-4o   │  Banking  │  Upstash  │  + pgvector + RLS    │
└──────────┴───────────┴───────────┴───────────────────────┘
```

---

## Features

### Core Features

| # | Feature | Description |
|---|---------|-------------|
| F1 | **Financial Dashboard** | Real-time cash flow, P&L, balance sheet, burn rate, runway, and custom KPIs by business type |
| F2 | **AI Chat Assistant** | RAG-backed conversational CFO — pulls from live financial data, never hallucinates, cites sources |
| F3 | **Cash Flow Forecasting** | 1–12 month projections with confidence bands and scenario modeling (e.g. "What if revenue drops 20%?") |
| F4 | **Proactive Alerts** | Automated notifications for low cash, short runway, overspending, revenue drops, and anomalies |
| F5 | **Budgeting & Goals** | Category-level budgets with progress tracking, goal setting with AI-powered trajectory commentary |
| F6 | **Anomaly Detection** | ML-powered detection (Isolation Forest) for duplicate charges, unusual transactions, and expense spikes |
| F7 | **Reporting & Exports** | Auto-generated cash flow statements, investor updates, and budget-vs-actuals reports |
| F8 | **Multi-User Roles** | Admin, CFO, Accountant, Investor, and Employee roles with granular permissions |
| F9 | **Integrations** | CSV upload, Plaid bank connections, and demo workspace with pre-loaded data |

### Bonus Features

| # | Feature | Description |
|---|---------|-------------|
| A | **Financial Health Score** | Composite 0–100 score based on runway, burn trend, budget variance, and revenue growth |
| B | **"What Can I Afford?" Calculator** | Instant impact analysis for hiring, purchases, and investments on runway and cash position |
| C | **Competitor Benchmarking** | Compare key metrics against industry averages (SaaS, D2C, Services) from static benchmark data |
| D | **Audit Trail** | Enterprise-grade change log for every forecast run, budget change, alert dismissal, and report export |

---

## API Endpoints

All endpoints are prefixed with `/api` and require Clerk JWT authentication.

| Router | Prefix | Description |
|--------|--------|-------------|
| Auth | `/api/auth` | User registration and JWT validation |
| Dashboard | `/api/dashboard` | Aggregated financial metrics and KPIs |
| Transactions | `/api/transactions` | CRUD + CSV import for financial transactions |
| Budgets | `/api/budgets` | Category-level budget management |
| Alerts | `/api/alerts` | Alert configuration and notification delivery |
| Chat | `/api/chat` | AI assistant with SSE streaming responses |
| Forecasting | `/api/forecasting` | Cash flow projections and scenario modeling |
| Anomaly | `/api/anomaly` | ML-driven anomaly detection results |
| Health Score | `/api/health-score` | Composite financial health calculation |
| Reports | `/api/reports` | Report generation and export |
| Settings | `/api/settings` | Workspace and notification preferences |
| Calculator | `/api/calculator` | Affordability impact analysis |
| Goals | `/api/goals` | Financial goal tracking |
| Audit | `/api/audit` | Immutable audit log queries |
| Benchmarks | `/api/benchmarks` | Industry benchmark comparisons |
| Onboarding | `/api/onboarding` | Business type and workspace setup |
| Plaid | `/api/plaid` | Bank connection and webhook handling |
| Search | `/api/search` | Semantic search over financial data |
| Health | `/api/health` | System health check |

---

## Getting Started

### Prerequisites

- **Node.js** ≥ 18
- **Python** ≥ 3.11
- **PostgreSQL** (or [Neon](https://neon.tech) serverless Postgres)
- **Redis** (or [Upstash](https://upstash.com) serverless Redis)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database URL, API keys, etc.

# Run database migrations
alembic upgrade head

# Seed demo data (Luna Bakery workspace)
python seed_demo.py

# Start the server
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
# Create .env.local with:
#   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxx
#   NEXT_PUBLIC_API_URL=http://localhost:8000

# Start dev server
npm run dev
```

The app will be available at `http://localhost:3000`.

### Environment Variables

See [`backend/.env.example`](backend/.env.example) for the full list of required environment variables covering:

- **Database** — Neon PostgreSQL connection string
- **Cache** — Upstash Redis URL and TTL
- **Auth** — Clerk secret key, publishable key, JWKS URL
- **AI** — OpenAI API key and model selection
- **Encryption** — Fernet key for field-level encryption
- **Observability** — OpenTelemetry exporter endpoint
- **Banking** — Plaid client ID, secret, and environment
- **Embeddings** — Model name and vector dimensions

---

## Database Migrations

The project uses **Alembic** for schema management with two initial migrations:

| Migration | Description |
|-----------|-------------|
| `001_enable_rls` | Enables PostgreSQL Row-Level Security on workspace-scoped tables |
| `002_add_pgvector` | Installs the pgvector extension and creates the embeddings table |

```bash
# Apply all migrations
cd backend
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description_here"
```

---

## Project Structure

```
CFO/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Pydantic settings from .env
│   ├── database.py             # Async SQLAlchemy engine + session
│   ├── models.py               # SQLAlchemy ORM models (25+ tables)
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── auth.py                 # Clerk JWT validation middleware
│   ├── cache.py                # Redis read-through cache layer
│   ├── crypto.py               # Fernet field-level encryption
│   ├── telemetry.py            # OpenTelemetry instrumentation
│   ├── seed_demo.py            # Luna Bakery demo data seeder
│   ├── alembic/                # Database migration scripts
│   ├── routers/                # 18 API route modules
│   ├── services/               # Business logic layer
│   │   ├── chat_service.py     # OpenAI RAG pipeline
│   │   ├── forecast_service.py # Cash flow projection engine
│   │   ├── anomaly_service.py  # Isolation Forest anomaly detection
│   │   ├── health_score_service.py
│   │   ├── plaid_service.py    # Plaid banking integration
│   │   ├── embedding_service.py # pgvector semantic search
│   │   └── ...
│   └── tests/                  # Test suite
├── frontend/
│   ├── app/
│   │   ├── layout.tsx          # Root layout with Clerk provider
│   │   ├── (app)/              # Authenticated app routes
│   │   │   ├── dashboard/      # Financial dashboard
│   │   │   ├── chat/           # AI assistant interface
│   │   │   ├── forecasting/    # Cash flow forecasting
│   │   │   ├── transactions/   # Transaction management
│   │   │   ├── budgets/        # Budget tracking
│   │   │   ├── goals/          # Financial goals
│   │   │   ├── alerts/         # Alert center
│   │   │   ├── anomalies/      # Anomaly detection
│   │   │   ├── reports/        # Report generation
│   │   │   ├── calculator/     # Affordability calculator
│   │   │   ├── investor/       # Investor-only dashboard
│   │   │   ├── audit/          # Audit trail viewer
│   │   │   ├── settings/       # Workspace settings
│   │   │   └── users/          # User & role management
│   │   ├── sign-in/            # Clerk sign-in page
│   │   └── sign-up/            # Clerk sign-up page
│   ├── components/             # Reusable UI components
│   ├── lib/
│   │   ├── api.ts              # Typed API client
│   │   └── types.ts            # Shared TypeScript interfaces
│   └── middleware.ts           # Clerk auth middleware
└── README.md
```

---

## Demo Workspace — Luna Bakery

The platform ships with a pre-loaded demo workspace for **Luna Bakery**, a fictional Mumbai-based bakery with:

- ₹30L/month revenue, 12% MoM growth
- 8 months of runway
- Rising raw material costs
- Marketing overspend flagged by anomaly detection
- Pre-configured budgets, goals, and alerts

Run `python seed_demo.py` to populate the demo data.

---

## License

This project is developed as a college MVP. All AI-generated outputs include appropriate confidence labels and data disclaimers. Financial reports are for internal planning purposes only — consult a qualified accountant for official financial statements.
