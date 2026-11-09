import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, api, type DocumentOut } from "../api/client";

export function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setDocs(await api.listDocuments());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load documents.");
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Poll while any document is still processing, so status updates live.
  useEffect(() => {
    const hasPending = docs.some((d) => d.status === "pending" || d.status === "processing");
    if (!hasPending) return;
    const t = setInterval(() => void load(), 2000);
    return () => clearInterval(t);
  }, [docs, load]);

  async function onUpload(file: File) {
    setError(null);
    setUploading(true);
    try {
      await api.uploadDocument(file);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
      if (fileInput.current) fileInput.current.value = "";
    }
  }

  async function onDelete(id: string) {
    try {
      await api.deleteDocument(id);
      await load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Delete failed.");
    }
  }

  return (
    <section className="page">
      <div className="page__head">
        <h2>Documents</h2>
        <label className="btn btn--primary">
          {uploading ? "Uploading..." : "Upload PDF / DOCX"}
          <input
            ref={fileInput}
            type="file"
            accept=".pdf,.docx"
            hidden
            disabled={uploading}
            onChange={(e) => e.target.files?.[0] && onUpload(e.target.files[0])}
          />
        </label>
      </div>

      {error && <p className="banner banner--error" role="alert">{error}</p>}

      {docs.length === 0 ? (
        <div className="empty">No documents yet. Upload one to get started.</div>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Pages</th>
              <th>Chunks</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>{d.filename}</td>
                <td>
                  <span className={`status status--${d.status}`}>{d.status}</span>
                  {d.status === "failed" && d.error && (
                    <span className="status-error" title={d.error}> — {d.error.slice(0, 60)}</span>
                  )}
                </td>
                <td>{d.page_count ?? "—"}</td>
                <td>{d.chunk_count}</td>
                <td>
                  <button className="btn btn--ghost" onClick={() => onDelete(d.id)}>
                    Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
