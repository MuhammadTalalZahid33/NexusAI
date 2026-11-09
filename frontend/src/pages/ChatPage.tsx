import { useState, type FormEvent } from "react";
import { ApiError, api, type Citation } from "../api/client";

interface Turn {
  question: string;
  answer: string;
  abstained: boolean;
  citations: Citation[];
}

export function ChatPage() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [agentic, setAgentic] = useState(false);
  const [openCitation, setOpenCitation] = useState<Citation | null>(null);

  async function onAsk(e: FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.ask(q, { agentic });
      setTurns((prev) => [
        ...prev,
        { question: q, answer: res.answer, abstained: res.abstained, citations: res.citations },
      ]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Request failed.");
    } finally {
      setBusy(false);
    }
  }

  // Render [n] markers as clickable citation chips.
  function renderAnswer(turn: Turn) {
    const parts = turn.answer.split(/(\[\d+\])/g);
    return parts.map((part, i) => {
      const m = part.match(/^\[(\d+)\]$/);
      if (m) {
        const marker = Number(m[1]);
        const cite = turn.citations.find((c) => c.marker === marker);
        if (cite) {
          return (
            <button key={i} className="cite-chip" onClick={() => setOpenCitation(cite)}>
              {part}
            </button>
          );
        }
      }
      return <span key={i}>{part}</span>;
    });
  }

  return (
    <section className="page chat">
      <div className="page__head">
        <h2>Ask</h2>
        <label className="toggle">
          <input type="checkbox" checked={agentic} onChange={(e) => setAgentic(e.target.checked)} />
          Agentic mode
        </label>
      </div>

      <div className="chat__log">
        {turns.length === 0 && (
          <div className="empty">Ask a question about your uploaded documents.</div>
        )}
        {turns.map((turn, i) => (
          <div key={i} className="turn">
            <div className="turn__q">{turn.question}</div>
            <div className={`turn__a ${turn.abstained ? "turn__a--abstain" : ""}`}>
              {turn.abstained ? (
                <em>Not enough evidence in your documents to answer this.</em>
              ) : (
                renderAnswer(turn)
              )}
            </div>
            {turn.citations.length > 0 && (
              <div className="turn__sources">
                {turn.citations.map((c) => (
                  <button key={c.marker} className="source-pill" onClick={() => setOpenCitation(c)}>
                    [{c.marker}] {c.filename}
                    {c.page_number ? ` · p.${c.page_number}` : ""}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {error && <p className="banner banner--error" role="alert">{error}</p>}

      <form className="chat__input" onSubmit={onAsk}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question..."
          disabled={busy}
        />
        <button className="btn btn--primary" type="submit" disabled={busy || !question.trim()}>
          {busy ? "Thinking..." : "Ask"}
        </button>
      </form>

      {openCitation && (
        <div className="drawer-backdrop" onClick={() => setOpenCitation(null)}>
          <aside className="drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer__head">
              <strong>
                {openCitation.filename}
                {openCitation.page_number ? ` · page ${openCitation.page_number}` : ""}
              </strong>
              <button className="btn btn--ghost" onClick={() => setOpenCitation(null)}>
                Close
              </button>
            </div>
            <p className="drawer__excerpt">{openCitation.text}</p>
          </aside>
        </div>
      )}
    </section>
  );
}
