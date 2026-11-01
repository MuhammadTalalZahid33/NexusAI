import { useEffect, useState } from "react";
import "./App.css";
import { ApiError, API_BASE_URL, getHealth, type HealthResponse } from "./api/client";

type Status = "loading" | "ok" | "error";

function App() {
  const [status, setStatus] = useState<Status>("loading");
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function checkHealth() {
    setStatus("loading");
    setError(null);
    try {
      const result = await getHealth();
      setHealth(result);
      setStatus("ok");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Unexpected error.";
      setError(message);
      setStatus("error");
    }
  }

  // Check backend health once on mount.
  useEffect(() => {
    void checkHealth();
  }, []);

  return (
    <main className="app">
      <header className="app__header">
        <h1 className="app__title">Nexus AI</h1>
        <p className="app__subtitle">Agentic RAG Knowledge Intelligence Platform</p>
      </header>

      <section className="card" aria-live="polite">
        <div className="card__row">
          <span className="card__label">Backend status</span>
          <StatusBadge status={status} />
        </div>

        {status === "ok" && health && (
          <dl className="card__meta">
            <div>
              <dt>Environment</dt>
              <dd>{health.app_env}</dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>{health.version}</dd>
            </div>
          </dl>
        )}

        {status === "error" && (
          <p className="card__error" role="alert">
            {error}
          </p>
        )}

        <div className="card__footer">
          <span className="card__api">{API_BASE_URL}</span>
          <button className="btn" type="button" onClick={() => void checkHealth()}>
            Re-check
          </button>
        </div>
      </section>

      <footer className="app__footer">
        <p>Milestone 1 &middot; project foundation</p>
      </footer>
    </main>
  );
}

function StatusBadge({ status }: { status: Status }) {
  const label = status === "loading" ? "Checking..." : status === "ok" ? "Healthy" : "Unreachable";
  return <span className={`badge badge--${status}`}>{label}</span>;
}

export default App;
