import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import "./App.css";
import { useAuth } from "./auth/AuthContext";
import { ChatPage } from "./pages/ChatPage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { LoginPage } from "./pages/LoginPage";

function Shell() {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebar__logo">Nexus AI</div>
        <nav className="sidebar__nav">
          <NavLink to="/" end>Ask</NavLink>
          <NavLink to="/documents">Documents</NavLink>
        </nav>
        <div className="sidebar__foot">
          <div className="sidebar__user">{user?.email}</div>
          <div className="sidebar__org">{user?.role}</div>
          <button className="btn btn--ghost" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  const { token, loading } = useAuth();
  if (loading) return <div className="loading-screen">Loading…</div>;
  if (!token) return <LoginPage />;
  return <Shell />;
}

export default App;
