import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/Authcontext.jsx';
import { ToastProvider } from './context/Toastcontext.jsx';
import Layout from './components/Layout.jsx';
import LoginPage from './pages/Loginpage.jsx';
import SignupPage from './pages/Signuppage.jsx';
import DemoPage from './pages/Demopage.jsx';
import ChatPage from './pages/Chatpage.jsx';
import HistoryPage from './pages/Historypage.jsx';
import FilesPage from './pages/Filespage.jsx';
import AllFeedbacksPage from './pages/Allfeedbackspage.jsx';
import AboutPage from './pages/Aboutpage.jsx';

function RequireSession({ children }) {
  const { isAuthenticated, isDemo } = useAuth();
  if (!isAuthenticated && !isDemo) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function AppRoutes() {
  const { isAuthenticated, isDemo } = useAuth();
  const hasSession = isAuthenticated || isDemo;

  return (
    <Routes>
      <Route path="/login" element={hasSession ? <Navigate to="/chat/new" replace /> : <LoginPage />} />
      <Route path="/signup" element={hasSession ? <Navigate to="/chat/new" replace /> : <SignupPage />} />
      <Route path="/demo" element={hasSession ? <Navigate to="/chat/new" replace /> : <DemoPage />} />

      <Route path="/about" element={hasSession ? <RequireSession><AboutPage /></RequireSession> : <AboutPage />} />

      <Route path="/chat/:threadId" element={<RequireSession><ChatPage /></RequireSession>} />
      <Route path="/history" element={<RequireSession><HistoryPage /></RequireSession>} />
      <Route path="/files" element={<RequireSession><FilesPage /></RequireSession>} />
      <Route path="/feedbacks" element={<RequireSession><AllFeedbacksPage /></RequireSession>} />

      <Route path="*" element={<Navigate to={hasSession ? '/chat/new' : '/login'} replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <ToastProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </ToastProvider>
    </AuthProvider>
  );
}