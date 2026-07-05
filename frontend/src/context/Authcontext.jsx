import { createContext, useContext, useState, useCallback } from 'react';
import { api } from '../api/client.js';

const AuthContext = createContext(null);

const LS_TOKEN = 'gha_token';
const LS_USERNAME = 'gha_username';
const LS_GUEST_ID = 'gha_guest_id';

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(LS_TOKEN));
  const [username, setUsername] = useState(() => localStorage.getItem(LS_USERNAME));
  const [guestId, setGuestId] = useState(() => localStorage.getItem(LS_GUEST_ID));

  const persistAuth = useCallback((tok, user) => {
    localStorage.setItem(LS_TOKEN, tok);
    localStorage.setItem(LS_USERNAME, user);
    localStorage.removeItem(LS_GUEST_ID);
    setToken(tok);
    setUsername(user);
    setGuestId(null);
  }, []);

  const signup = useCallback(async ({ username, password, github_token, groq_api_key }) => {
    const res = await api.signup({ username, password, github_token, groq_api_key });
    persistAuth(res.access_token, username);
    return res;
  }, [persistAuth]);

  const login = useCallback(async ({ username, password }) => {
    const res = await api.login({ username, password });
    persistAuth(res.access_token, username);
    return res;
  }, [persistAuth]);

  const logout = useCallback(() => {
    localStorage.removeItem(LS_TOKEN);
    localStorage.removeItem(LS_USERNAME);
    setToken(null);
    setUsername(null);
  }, []);

  const setDemoSession = useCallback((id) => {
    localStorage.setItem(LS_GUEST_ID, id);
    setGuestId(id);
  }, []);

  const clearDemoSession = useCallback(() => {
    localStorage.removeItem(LS_GUEST_ID);
    setGuestId(null);
  }, []);

  const isAuthenticated = Boolean(token && username);
  const isDemo = Boolean(guestId) && !isAuthenticated;

  return (
    <AuthContext.Provider
      value={{
        token, username, guestId,
        isAuthenticated, isDemo,
        signup, login, logout,
        setDemoSession, clearDemoSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}