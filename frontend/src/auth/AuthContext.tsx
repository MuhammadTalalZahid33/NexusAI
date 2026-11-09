/**
 * Authentication context: holds the JWT + current user, persists the token to
 * localStorage, and wires it into the API client. Components read auth state
 * via the useAuth() hook.
 */

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, setAuthToken, type Me } from "../api/client";

interface AuthState {
  token: string | null;
  user: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, org: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);
const TOKEN_KEY = "nexus_token";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  // Keep the API client + localStorage in sync with the token.
  useEffect(() => {
    setAuthToken(token);
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  }, [token]);

  // On load (or token change), resolve the current user.
  useEffect(() => {
    let cancelled = false;
    async function loadUser() {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }
      try {
        const me = await api.me();
        if (!cancelled) setUser(me);
      } catch {
        if (!cancelled) setToken(null); // invalid/expired token
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    setLoading(true);
    void loadUser();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const value = useMemo<AuthState>(
    () => ({
      token,
      user,
      loading,
      login: async (email, password) => {
        const r = await api.login(email, password);
        setToken(r.access_token);
      },
      register: async (email, password, org) => {
        const r = await api.register(email, password, org);
        setToken(r.access_token);
      },
      logout: () => setToken(null),
    }),
    [token, user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
