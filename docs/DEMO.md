# Demo Script

A 5-minute walkthrough for a live demo or screen recording.

## Setup (once)

1. `Copy-Item .env.example .env`, set `DATABASE_URL` (Neon).
2. (Optional, for best quality) set `GEMINI_API_KEY` and `COHERE_API_KEY`.
3. Start backend + frontend (see README Quick start) or `docker compose up`.

## Script

1. **Sign up.** Open the app, create an account with an organization name. Note
   you land in an empty, isolated workspace.

2. **Upload a document.** Go to Documents, upload a PDF. Watch the status move
   `pending → processing → ready` live (the UI polls). Point out page count and
   chunk count — the document was extracted, chunked, and embedded
   asynchronously.

3. **Ask a grounded question.** Go to Ask, enter a question answerable from the
   document. Show:
   - the answer with inline `[1]` citation chips,
   - the source pills below,
   - clicking a citation opens a drawer with the exact passage and page number.
   This is the "verifiable citations" story.

4. **Ask an unanswerable question.** Ask something not in the documents. Show the
   system **abstains** ("not enough evidence") instead of hallucinating. This is
   the honesty/groundedness story.

5. **Toggle Agentic mode.** Re-ask a harder/compound question with the toggle on.
   Explain the bounded workflow: classify → rewrite → retrieve → assess → escalate
   if weak → generate → validate — with hard retry caps.

6. **Show evaluation.** In a terminal, run `python -m app.eval.runner` and open
   the report. Explain Recall@k / MRR / nDCG and the strategy comparison — the
   "measured, not claimed" story.

7. **Show the widget.** Create a public API key (`POST /widget/keys` in
   `/docs`), paste it into `widget/demo.html`, open the page, and chat via the
   embedded bubble — anonymous, tenant-scoped by the key.

8. **Show security.** Mention: org isolation enforced in SQL (integration test),
   prompt-injection defenses, API-key hashing, rate limiting.

## Talking points (interview)

- Why hybrid + rerank, and how retrieve-then-rerank works.
- Why the agent is bounded and mostly deterministic.
- How tenant isolation is a database boundary, not frontend filtering.
- How providers are swappable (free stubs → Gemini/Cohere) with no code change.
- What you did NOT build and why (non-goals): no microservices, no OCR yet,
  small eval set — and the upgrade path for each.
