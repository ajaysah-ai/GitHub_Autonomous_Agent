import { createContext, useContext, useState, useCallback } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toast, setToast] = useState(null);

  const showToast = useCallback((message, tone = 'neutral') => {
    const id = Date.now();
    setToast({ message, tone, id });
    setTimeout(() => setToast((t) => (t && t.id === id ? null : t)), 3200);
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {toast && (
        <div className="toast" style={{ borderColor: toast.tone === 'danger' ? 'var(--danger)' : toast.tone === 'ok' ? 'var(--ok)' : 'var(--border)' }}>
          {toast.message}
        </div>
      )}
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>');
  return ctx;
}