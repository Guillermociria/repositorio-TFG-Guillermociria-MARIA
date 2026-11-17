# MARIA — Configurable AI-Assisted Innovation Process for Requirements Engineering

This repository contains the **proof of concept** that accompanies the paper
*"From Needs to Prototypes: A Configurable AI-Assisted Innovation Process for Requirements Engineering"* (under review).

The paper proposes a configurable, AI-assisted discovery process that combines Design Thinking (DT) and
Design Sprint (DS). It is organised in three groups of stages: **requirements engineering** (understand, define),
**analysis** (ideate, decide) and **sprint outcome** (prototype, validate). The requirements engineer
chooses and orders techniques from a shared catalogue. An AI harness runs each technique, and the engineer
approves or regenerates every result.

This proof of concept implements the backbone of that process:

- A **technique catalogue** grouped by stage. You can extend it with custom techniques through a form in the web UI.
- **Session composition**: the engineer selects techniques and drags them into the desired order.
- An **LLM agent** (LangGraph) that runs each technique in sequence. After every technique there is a
  human-in-the-loop checkpoint where the engineer can **approve** the result or **regenerate** it with feedback.
  They can also edit the technique's prompt before regenerating.
- **Multiple LLM providers**: Google Gemini, OpenAI GPT or Anthropic Claude.
- A **self-correction loop** (generate → validate → fix, up to 3 retries) for the structured Design Sprint techniques.
- **Variability modelling** with the Universal Variability Language (UVL): a feature model for the whole platform.
  Defining techniques as UVL files is **still in development** (see [below](#technique-variability-with-uvl-in-development)).
- **Export** of a completed session as JSON.

> **Note:** The user interface and most prompts are in **Spanish**.
> These parts of the paper's vision are **not implemented yet**: the harness steps beyond regeneration
> (dimension selection, technique recommendation, option diversification), the *validator* role and the *researcher* participant.

---

## Repository structure

```
.
├── maria/                      # Django project (the web platform)
│   ├── maria/                  # Django settings, URLs, WSGI/ASGI
│   ├── home/                   # Landing page and feature-model configuration form
│   ├── user/                   # Custom user model (stores per-user LLM API keys), login/registration/profile
│   ├── llm/                    # Sprint sessions, technique catalogue, bridge between Django and LangGraph
│   │   ├── models.py           #   SprintSession, Technique
│   │   ├── services.py         #   Runs the LangGraph agent, Postgres checkpointer pool
│   │   ├── uvl_parser.py       #   Parser for technique UVL files
│   │   └── management/commands/
│   │       ├── seed_techniques.py       # Loads the built-in technique catalogue
│   │       ├── import_technique_uvl.py  # Imports techniques from .uvl files (in development)
│   │       └── setup_langgraph.py       # Creates LangGraph checkpoint tables
│   ├── nodes/                  # LangGraph agent
│   │   ├── llm.py              #   LLM factory, technique registry and master graph
│   │   ├── ltg/ sq/ map/ generate_map/ hmw/ rapidPrototype/
│   │   │                       #   Per-technique subgraphs (generate → validate → fix)
│   │   └── common/             #   Shared router / fallback nodes
│   ├── state/                  # Typed agent state and output schemas
│   ├── prompts/                # Default prompt for each technique (.txt templates)
│   ├── techniques/             # Example technique defined in UVL (in development)
│   ├── templates/              # Shared Django templates (dashboard, catalogue, auth)
│   ├── utils/                  # Prompt loader
│   ├── Dockerfile
│   ├── docker-compose.local.yml  # Local setup (recommended)
│   ├── docker-compose.yml        # Server deployment behind nginx + TLS
│   ├── .env.example              # Every configurable environment variable
│   └── requirements.txt
├── maria.uvl                   # Feature model of the whole platform (stages, techniques, LLM providers, constraints)
├── technique_schema.uvl        # Draft template for technique UVL files (in development)
├── tests_playwright/           # End-to-end UI tests (Playwright)
├── locustfile.py               # Load tests (Locust)
└── pytest.ini                  # Pytest config for the Playwright tests
```

`main.py`, `prompting.py`, `plantilla.txt`, `resultado.txt`, `config/` and `graph/` are early experiments.
The platform does not use them.

### How the agent works

The master graph in [maria/nodes/llm.py](maria/nodes/llm.py) loops over the techniques the engineer selected:

```
pre_technique ──► run_technique ──► (engineer reviews)
     ▲                 ▲                  │
     │                 └── feedback ──────┤
     │                                    ▼ approve
     └──────── more techniques ◄── advance_technique ──► END
```

- `pre_technique`: an interrupt point where the engineer answers the technique's optional questionnaire.
- `run_technique`: runs the technique with its prompt (the default prompt, or the engineer's edited prompt).
  The prompt receives the project inputs (problem, target user, pain points, initial idea) and the outputs of the techniques that were already approved.
- A Postgres checkpointer stores the graph state, so each session can be paused and resumed.

### Built-in technique catalogue

| Paper stage | Stage in code | Techniques |
|---|---|---|
| Understand | `empatizar` | Empathy map, In-depth interviews, Customer Journey Map |
| Define | `definir` | Long Term Goal, Sprint Questions, How Might We, Point of View |
| Ideate / Decide | `idear` | Brainstorming |
| Prototype | `prototipar` | Rapid prototyping |
| Validate | `testear` | User testing |

The agent registry also contains the Design Sprint *Map* and *Generate Map* techniques. Their dependencies are
declared as constraints in [maria.uvl](maria.uvl).

### Adding custom techniques

To add a technique, use the form in the web UI (**Catalogue → create**). For each technique you set its name,
stage, default prompt and an optional questionnaire that the engineer answers before the technique runs.

Prompts can use the placeholders `{problem_definition}`, `{target_user}`, `{pain_points}`,
`{initial_idea}` and `{previous_context}`. A prompt must ask the model to return only JSON.

### Technique variability with UVL (in development)

The paper's vision has the researcher publish a UVL model with each validated technique. This part is **work in
progress and is not usable yet**. The repository contains the draft pieces:
[technique_schema.uvl](technique_schema.uvl) (template), [maria/techniques/entrevistas.uvl](maria/techniques/entrevistas.uvl)
(example), [maria/llm/uvl_parser.py](maria/llm/uvl_parser.py) and the `import_technique_uvl` management command.
The web UI does not support importing techniques from UVL.

---

## Getting started

### Requirements

- **Docker** and **Docker Compose** (recommended), *or* Python 3.13 and PostgreSQL 15
- At least one LLM API key. A **Google Gemini** key is required to start the app, because Gemini is the default
  provider. OpenAI and Anthropic keys are optional. Each user can also add their own keys on their profile page.

### 1. Configure the environment

All configuration comes from environment variables. Copy the template and fill in at least `GEMINI_API_KEY`:

```bash
cd maria
cp .env.example .env
```

Django reads `maria/.env` automatically, and Docker Compose uses it for variable substitution. Every variable
has a default that works on a local machine, so only the API key is required. The main groups are:

| Variables | Purpose |
|---|---|
| `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | LLM providers (Gemini is required) |
| `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS` | Django settings (lists are comma-separated) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | PostgreSQL database for Django |
| `LANGGRAPH_DB_URI` (or `LANGGRAPH_DB_USER` / `_PASSWORD` / `_NAME` with Docker) | Database for LangGraph checkpoints; outside Docker it defaults to the Django database |
| `WEB_PORT` | Host port for the app with `docker-compose.local.yml` (default `8000`) |
| `DEMO_USER`, `DEMO_PASSWORD`, `DEMO_USERS_PASSWORD` | Credentials of the seeded demo accounts |
| `DJANGO_BASE_URL`, `PW_TEST_USER`, `PW_TEST_PASS`, `PERF_TEST_USER`, `PERF_TEST_PASS` | Target URL and accounts for the Playwright and Locust tests |

### 2a. Run with Docker (recommended)

```bash
cd maria
docker compose -f docker-compose.local.yml up --build
```

This starts two PostgreSQL containers (one for Django data, one for LangGraph checkpoints) and the web app.
On startup the app automatically:

1. creates and applies migrations,
2. seeds the technique catalogue (`seed_techniques`),
3. creates demo users (`seed_user`, `seed_demo_users`),
4. creates the LangGraph checkpoint tables (`setup_langgraph`),
5. serves the app with Gunicorn.

Open **http://localhost:8000** (or the port set in `WEB_PORT`).

> `docker-compose.yml` is for a server deployment behind nginx with TLS. It expects an nginx config (`NGINX_CONF`,
> default `./nginx.conf`, not included in this repository) and a certificates folder (`CERTS_DIR`). Use
> `docker-compose.local.yml` for local runs.

### 2b. Run without Docker

You need Python 3.13 and a running PostgreSQL database that matches the `DB_*` variables in `.env`.

```bash
cd maria
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python manage.py makemigrations
python manage.py migrate
python manage.py seed_techniques
python manage.py seed_user
python manage.py setup_langgraph
python manage.py runserver
```

### 3. Use the platform

1. Log in with the demo account (by default **`demo` / `demo1234`**; set by `DEMO_USER` / `DEMO_PASSWORD`), or
   register a new user. `seed_demo_users` also creates the accounts `demo01`…`demo35`, whose password is
   `DEMO_USERS_PASSWORD` (default `demo123`).
2. Optional: on the **Profile** page, add your own OpenAI or Anthropic API key. GPT-4o and Claude become
   available as providers only after you add a key; Gemini 2.5 Flash is always available.
3. On the **Dashboard**, create a sprint session and enter the problem definition, target user, pain points and initial idea.
4. Select techniques from the catalogue, put them in order and choose the LLM provider for each technique.
5. For each technique, answer its questionnaire (if it has one), review the output, and then **approve** it or give
   feedback (and optionally edit the prompt) to **regenerate** it.
6. When the session is complete, export the results as JSON.

---

## Tests

| Kind | Location | How to run |
|---|---|---|
| Unit and integration (Django; the LangGraph agent is mocked) | `maria/*/tests.py`, `maria/llm/test_integration.py` | `cd maria && python manage.py makemigrations && python manage.py test` |
| End-to-end UI (Playwright) | `tests_playwright/` | Start the server, then run `python manage.py seed_tests`, `playwright install chromium` and `pytest tests_playwright/ -v` |
| Load (Locust) | `locustfile.py` | Start the server, then run `python manage.py seed_tests` and `locust -f locustfile.py --host http://localhost:8000` |

- The unit and integration tests use a temporary SQLite database, so they don't need PostgreSQL or a real API key.
  `GEMINI_API_KEY` must still be set, but any value works.
- Migrations are not committed, which is why `makemigrations` comes first.
- The Playwright and Locust tests read the server URL and test accounts from the `DJANGO_BASE_URL`, `PW_TEST_*` and
  `PERF_TEST_*` variables. `seed_tests` creates those accounts with the same values.
- With Docker, run the commands inside the container, for example `docker exec django_web python manage.py test`.

---

## Security notice

This is a research prototype. The defaults in `.env.example` (secret key, `DJANGO_DEBUG=True`, database and demo
passwords) are only for local use. Change them before you expose the app on a network.
