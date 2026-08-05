# Build Roadmap: Pharma Regulatory Research Assistant ("RegIntel")

**Who this is for:** ~1 year experience, solid Python basics, learning every other layer (FastAPI, RAG, LangGraph, evaluation, Docker, cloud, LLMOps) from scratch.

**Timeline:** 12 weeks at ~10–12 hrs/week. If you can do more, compress — don't skip phases.

**Total cost:** ₹0 if you stay inside free tiers (details in each phase).

---

## Why this topic instead of another finance bot

You already have a financial RAG project on your resume. Building a second one teaches you nothing new *narratively*. This project instead targets the **life sciences / regulated-industry angle** that TraceLink-style employers explicitly value:

- **Data source:** openFDA API (free, no key needed for light use) — drug recalls, adverse events, drug approvals — plus a handful of FDA guidance PDFs.
- **What it does (final state):** *"Built an agentic RAG system that makes FDA data accessible in plain English — combining a pre-indexed corpus of FDA guidance documents with live openFDA API retrieval, so researchers, patients, and small biotech analysts can ask natural language questions about drug safety, recalls, and approvals without needing to understand FDA's data structure."* Concretely: a user asks something like *"Were there any Class I recalls of blood pressure medications in the last two years, and what caused them?"* The system routes the query, retrieves from your indexed corpus, pulls in live openFDA data or web search when the corpus can't answer, synthesizes corpus + web evidence for hybrid questions with citations, self-checks its answer, and escalates to the web before ever saying "I don't know."
- **Interview story it gives you:** "I built and deployed an agentic RAG system in a regulated-data domain, with automated evaluation and cost monitoring." That single sentence hits 5 of the gaps from your gap analysis.

The architecture is identical to any research assistant — swap the data source and everything below still applies.

---

## Ground rules (read before Week 1)

1. **Build the dumb version first, always.** Every phase produces something that *works end to end*, then the next phase upgrades one layer. Never let the project be broken for more than a day.
2. **One Git commit minimum per session.** Your commit history is evidence of learning. Recruiters do look.
3. **Keep a `LEARNING.md` in the repo.** Two lines per session: what you did, what confused you. This becomes your blog post material in Week 12 and your interview story bank.
4. **Don't add a tool because it's cool.** Every dependency must answer a problem you actually hit. This is the #1 difference between a 1-year engineer's project and a resume-padding project.

---

## Phase 0 — Setup & Python hygiene (Week 1, first half)

**Learn:**
- Git properly: branching, meaningful commits, .gitignore. Resource: *Learn Git Branching* (learngitbranching.js.org) — the interactive one, ~2 hours.
- Python project structure: virtual environments (`venv`), `requirements.txt`, `src/` layout, environment variables via `.env` + `python-dotenv`.
- How to read API docs. Practice target: openFDA docs (open.fda.gov/apis).

**Build:**
- Empty repo `regintel` on GitHub with README, .gitignore, venv, and one script `explore_fda.py` that calls the openFDA drug recall endpoint with `requests` and prints 5 recalls as clean JSON.

**Done when:** You can explain to someone what an API endpoint, query parameter, and JSON response are — using your own script as the example.

---

## Phase 1 — FastAPI backend fundamentals (Week 1 second half – Week 2)

**Learn:**
- FastAPI from zero: path/query params, request/response models with Pydantic, automatic Swagger docs, async basics (just enough — don't go down the asyncio rabbit hole yet).
- Resource: the official FastAPI tutorial (fastapi.tiangolo.com) — genuinely one of the best docs in software, do the first ~10 sections. Skip security/OAuth for now.
- Pydantic v2 models: this matters more than it looks; typed data models are how you'll keep LLM outputs sane later.
- LangChain's `Document` object (`page_content` + `metadata`) — just enough to know the shape, since your ingestion script will produce these directly instead of raw JSON. Don't touch loaders, splitters, or embeddings yet — that's Phase 3.

**Build:**
- `GET /recalls?drug=...&limit=...` → fetches from openFDA live, returns a typed Pydantic response.
- `GET /health` endpoint.
- A small ingestion script that pulls ~500–1,000 recall records + 5–10 FDA guidance PDFs (pick a theme, e.g., drug manufacturing quality) and saves them locally as LangChain `Document` objects (one `Document` per recall record and one per PDF page/section), each with metadata (source, date, doc type) attached at creation time — not as raw untyped JSON. Persist them (e.g. via `pickle` or a simple JSONL of `{page_content, metadata}` dicts you can reload into `Document`s) so Phase 3 loads a ready-made list of `Document`s instead of re-parsing raw files.

**Done when:** Swagger UI at `/docs` works, and you have a `data/` folder with a real corpus of `Document` objects. **Milestone commit + tag `v0.1`.**

---

## Phase 2 — Talking to an LLM with LangChain (Weeks 2–3)

**Learn:**
- How LLM APIs actually work: messages array, system prompts, temperature, max tokens, why outputs vary run to run.
- Structured outputs: forcing JSON out of a model and validating it with Pydantic (this is a daily-job skill for agentic AI roles). Use `.with_structured_output(YourPydanticModel)` on a LangChain chat model rather than hand-parsing JSON — but read what it's doing underneath (tool-calling or JSON-mode depending on the provider) so it isn't a black box.
- Prompt engineering basics: Anthropic's prompt engineering docs and OpenAI's cookbook are both free and enough. Skip paid courses.
- **Free LLM access:** Groq free tier (Llama 3.x models, fast, generous) and Google's Gemini free tier. Use LangChain's `ChatGroq` and `ChatGoogleGenerativeAI` wrappers instead of the raw provider SDKs — same chat model interface, so the exact same object plugs straight into Phase 3's LCEL chains with no rewrite. Use one as primary, keep the other as backup. Wrap model construction in one `llm.py` module (a `get_llm()` function) so switching providers is a one-line change — you'll thank yourself in Phase 8.

**Build:**
- `POST /summarize-recall`: takes a recall record, returns an LLM-written plain-English summary with a structured risk classification (Pydantic-validated JSON: `{severity, affected_population, root_cause_category}`) via `.with_structured_output()`.
- Deliberately break it: feed it weird inputs, watch structured output fail to fill required fields, add retry-on-validation-error logic (LangChain raises a validation error you can catch and retry on, same idea as hand-parsing, just less boilerplate). **This failure-handling experience is exactly what "non-deterministic behavior patterns" means in job posts.** Write down what broke in LEARNING.md.

**Done when:** The endpoint survives 20 varied inputs without crashing. Tag `v0.2`.

---

## Phase 3 — RAG v1 with LangChain (Weeks 3–5)

This is the heart of the project. Take the full two weeks.

**Learn (in this order):**
1. What embeddings are — watch 3Blue1Brown's word embedding material or Jay Alammar's "Illustrated Word2Vec" for intuition, then use `sentence-transformers` (BGE-small, local, free, runs on CPU) via LangChain's `HuggingFaceEmbeddings` wrapper.
2. Chunking: why it matters, fixed-size vs. recursive splitting. Use LangChain's `RecursiveCharacterTextSplitter` at ~800 tokens with overlap. Don't research "optimal chunking" for days — pick, build, measure later.
3. Vector stores: LangChain's `Chroma` integration (local, free, simple). Understand what `similarity_search` actually returns under the hood — a list of `Document` objects with `page_content` and `metadata`, ranked by distance.
4. LCEL basics (`prompt | llm | parser`) and how a retrieval chain composes: retriever → format docs → prompt → LLM → parse.

**One rule to keep this honest:** for every LangChain class you use, be able to say what it's doing without the abstraction — e.g. "`Chroma.from_documents` embeds each chunk and stores the vector + metadata + original text" — not just "it makes a vector store." If you can't say that in one sentence, spend 10 minutes reading that class's source or docs before moving on. This is what stops "I used LangChain" from being your whole answer in an interview.

**Build:**
- `ingest.py`: load the `Document` objects your Phase 1 script already produced (recall records + guidance PDFs, metadata already attached) → `RecursiveCharacterTextSplitter` to chunk them → `HuggingFaceEmbeddings` (BGE-small, local) → `Chroma.from_documents()`, persisted to disk. Chunking preserves each `Document`'s existing metadata onto its chunks automatically — a good moment to confirm that in practice, not just assume it.
- `POST /ask`: an LCEL chain — `Chroma.as_retriever(k=5)` → format retrieved docs into context → prompt template → LLM → parse into a structured answer. Return the answer *and* the retrieved `Document` objects (transparency = debuggability).
- Manually test with 15 questions you write yourself. Note which ones fail and *why* (bad retrieval? bad generation? answer not in corpus?). Save these 15 questions — they become your eval set in Phase 6.

**Done when:** you can trace one query through the whole chain on a whiteboard from memory — including what each LangChain class does internally, not just its name. Tag `v0.3`.

---

## Phase 4 — Hybrid retrieval with LangChain (Weeks 5–6)

**Learn:**
- Why dense retrieval fails on exact terms (drug names, recall numbers, regulation codes — your domain is full of them). This motivates keyword search.
- BM25 via LangChain's `BM25Retriever`, and Reciprocal Rank Fusion to merge BM25 + vector results via LangChain's `EnsembleRetriever` (start with roughly equal weights, e.g. 0.5/0.5). **Read the RRF algorithm yourself first** (it's ~15 lines of logic — reciprocal rank scores summed across retrievers) so you understand what `EnsembleRetriever` is doing before you lean on it. This is the same "don't let the framework be a black box" rule from Phase 3.

**Build:**
- Build a `BM25Retriever` over the same chunks as your Chroma vector store; combine both via `EnsembleRetriever`.
- Swap `EnsembleRetriever` in as the retriever in your Phase 3 LCEL chain — this should be close to a one-line change if Phase 3's chain was built cleanly around the retriever interface.
- Re-run your 15 test questions. Record before/after which improved. **This before/after comparison is a killer interview story** — "hybrid retrieval fixed 4 of my 6 failing queries because drug names weren't matching in dense-only search."

**Done when:** You have a small comparison table in LEARNING.md, and can explain in one sentence what `EnsembleRetriever` does with the two result lists it receives. Tag `v0.4`.

---

## Phase 5 — The agentic layer with LangGraph (Weeks 6–8)

Now, and only now, a framework — because you have a real problem it solves: routing and multi-step control flow.

**Learn:**
- LangGraph fundamentals: state, nodes, edges, conditional edges. Resource: the free LangChain Academy "Introduction to LangGraph" course — do modules 1–3, skip the rest.
- Agent design patterns: router, tool-calling, self-correction loop. Read Anthropic's "Building Effective Agents" essay (free, short, and the best thing written on when *not* to use agents).
- Web search as a tool: Tavily's API (free tier, 1,000 searches/month) — how to get clean, LLM-ready results and, critically, how to treat web content as *lower-trust context* than your curated corpus.

**Build a graph with ~7 nodes (in two passes):**

*Pass 1 — core graph (week 6–7):*
1. **Router** — classifies the query: `corpus` / `fresh_data` / `web` / `hybrid` / `out_of_scope`. "Hybrid" means the question needs both grounded corpus facts *and* current context (e.g., "Was the 2024 metformin recall related to the NDMA issues in the news?").
2. **Retriever** — your Phase 4 hybrid retrieval, wrapped as a node.
3. **Live-data tool** — hits openFDA API directly for recent-data questions (this is real "tool calling," not a toy).
4. **Generator** — answers with citations.
5. **Self-check** — grades its own answer for groundedness against the gathered context; if it fails, one retry with reformulated query. Cap retries at 1 — infinite loops are the classic beginner agent bug.

*Pass 2 — web search integration (week 7–8):*
6. **Web search node** — Tavily wrapped as a tool. It gets used in TWO ways, and this distinction is the whole design:
   - **Routed:** the router sends purely-current-events questions straight here (corpus can't answer "what did FDA announce this month").
   - **Escalation:** when self-check fails after the retry, escalate to web search instead of giving up — *then* answer, clearly labeled as web-sourced.
7. **Synthesizer** — for `hybrid` routes, merges corpus chunks + web results into one answer with **per-claim source attribution** (each claim tagged `[corpus: recall #123]` or `[web: fda.gov press release]`). This is the node that makes "RAG + web = better answers" real instead of just having two disconnected paths.

**Design rules to enforce (these are your interview talking points):**
- Corpus beats web on conflicts: if the corpus and a web result disagree on a fact the corpus covers, prefer the corpus and *say so* in the answer. Web content is unverified; your corpus is curated.
- Never let web results into the context silently — every web-sourced claim must carry its URL.
- Web search is capped at 1 call per query (cost + latency + your Tavily quota).

**Done when:** (a) "what was recalled *last week*" routes to the live API, (b) "what did the FDA announce about GLP-1 drugs this month" routes to web, (c) a hybrid question produces one answer citing both corpus chunks and URLs, and (d) an unanswerable corpus question escalates to web before admitting defeat. Tag `v0.5`.

*Time note: pass 2 adds roughly half a week. Take it from Phase 7 — Streamlit + Docker fits in one week if needed.*

---

## Phase 6 — Evaluation & testing (Weeks 8–9)

This phase is what separates you from 95% of candidates at your level. Do not skip or rush it.

**Learn:**
- RAG evaluation concepts: faithfulness, answer relevancy, context precision/recall. Use **RAGAS** (free) — but read what each metric computes rather than treating scores as magic numbers.
- Pytest basics: fixtures, parametrized tests.

**Build:**
- Grow your 15 questions into a golden dataset of ~30 with reference answers (LLM-draft them, then hand-correct — corpus is small enough). Tag each question with its *expected route* (corpus / fresh_data / web / hybrid / out_of_scope).
- `evals/` module: runs the pipeline over the golden set, computes RAGAS metrics, writes a report. Compute faithfulness against **whatever context was actually used** (corpus chunks, web results, or both) — that's how you evaluate web-augmented answers without pretending they came from the corpus.
- **Router accuracy eval:** the expected-route tags give you a free classification metric — % of queries routed correctly. Web-route answers change with the live web, so for those, assert on route correctness + citation presence rather than exact answer content.
- Pytest suite: unit tests for chunking, RRF, and JSON parsing; plus 5 "smoke" eval questions with score thresholds that must pass (use corpus-route questions for smoke tests — they're deterministic enough for CI).
- Change something (chunk size, top-k) and watch the metrics move. Now you're doing empirical engineering, not vibes.

**Done when:** `pytest` green, one eval report committed, and you can explain what faithfulness measures and one way it can be misleading. Tag `v0.6`.

---

## Phase 7 — UI + Docker (Weeks 9–10)

**Learn:**
- Streamlit: 2–3 hours from the official docs is enough for a chat UI.
- Docker from scratch: images vs. containers, Dockerfile, layers, docker-compose. Resource: Docker's own "Getting Started" + one weekend of breaking things. Learn `docker logs` and `docker exec` — debugging containers is the actual job skill.

**Build:**
- Streamlit chat UI calling your FastAPI backend, showing answer + cited sources + which route the agent took (that last detail impresses in demos).
- `Dockerfile` for the API, `docker-compose.yml` for API + UI.

**Done when:** A friend can run `docker compose up` on their machine and use it. Tag `v0.7`.

---

## Phase 8 — Cloud deployment + CI/CD (Weeks 10–11)

**Learn:**
- Pick **GCP Cloud Run** (simplest serverless container platform, has a permanent free tier) — AWS App Runner is the alternative if you prefer AWS on your resume.
- GitHub Actions: workflow triggers, jobs, secrets.
- Basics you'll hit whether you like it or not: container registries, environment variables in prod, cold starts.

**Build:**
- Deploy the FastAPI container to Cloud Run with a public URL. (Streamlit can run on Streamlit Community Cloud, free, pointing at your Cloud Run API.)
- GitHub Actions pipeline: on every PR → run pytest + the 5 smoke evals; on merge to main → build and deploy automatically. **Evals in CI is your single most differentiating line item.**
- Watch costs/quotas for a few days. Note: keep your ChromaDB small and baked into the image for simplicity — acknowledging that tradeoff out loud in interviews ("I chose an embedded store over a managed vector DB because...") is a senior-sounding move.

**Done when:** Pushing a commit to main updates the live URL with zero manual steps. Put the URL in your README and resume. Tag `v1.0`.

---

## Phase 9 — LLMOps + packaging the story (Weeks 11–12)

**Learn/Build:**
- Add **Langfuse** (free tier) tracing: every request logs the full agent path, latency, token counts, and cost per query. Add prompt versioning through Langfuse or just structured prompt files in Git.
- Set a simple cost guardrail (max tokens per request, request rate limit).
- **README overhaul:** architecture diagram, demo GIF, eval results table, "design decisions" section (why hybrid retrieval, why retry-once, why Cloud Run). This README is the first thing every hiring manager opens.
- 2-minute Loom demo video.
- One blog post (LinkedIn or dev.to) drawn from LEARNING.md: *"What broke when I built an agentic RAG system on FDA data — and how I tested for it."* Failure-focused posts read as more credible than success-focused ones.

**Done when:** You can answer, with evidence from your own dashboards: "What does an average query cost? Where does latency go? How do you know an update didn't make answers worse?" Those three questions are LLMOps in a nutshell — and they come up in interviews.

---

## Skills-to-gaps map (so you know why each phase exists)

| Phase | Resume gap it closes |
|---|---|
| 1–2 | Production-quality Python, APIs, structured LLM outputs |
| 3–4 | RAG depth beyond frameworks, retrieval quality reasoning |
| 5 | Agent orchestration, tool calling, non-deterministic behavior handling |
| 6 | Evaluation datasets, regression testing, behavior monitoring |
| 7–8 | **Cloud deployment (your #1 gap)**, CI/CD, Docker in prod |
| 9 | LLMOps: monitoring, cost, versioning (JD2's preferred list) |

## Free-tier stack summary

Python + FastAPI + Pydantic · Groq or Gemini free tier for the LLM · LangChain (chat model wrappers, structured output, embeddings, text splitting, Chroma + BM25 + Ensemble retrieval, LCEL) · sentence-transformers (BGE-small, local) · ChromaDB · LangGraph · Tavily free tier (web search, 1,000/month) · RAGAS + pytest · Streamlit · Docker · GCP Cloud Run + GitHub Actions · Langfuse free tier · openFDA (free)

## Where people at your level go wrong (avoid these)

1. Using LangChain/LangGraph without ever being able to explain what a class does underneath the abstraction.
2. Spending 3 weeks comparing vector databases instead of shipping with the first reasonable one.
3. Building 10 agent nodes because it feels impressive — 5 well-tested nodes beat 10 flaky ones every time.
4. Skipping Phase 6 because evaluation is boring. It's also the phase hiring managers ask about most.
5. Never deploying. A localhost project is a tutorial; a URL is a product.
