import { NavLink, useNavigate } from 'react-router-dom';
import { Terminal, MessageSquarePlus, History, FolderGit2, MessagesSquare, Info, LogOut, Menu } from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../context/Authcontext.jsx';

export default function Layout({ children }) {
  const { username, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  function handleExit() {
    logout();
    navigate('/login');
  }

  const links = [
    { to: '/chat/new', icon: MessageSquarePlus, label: 'New goal' },
    { to: '/history', icon: History, label: 'History' },
    { to: '/files', icon: FolderGit2, label: 'Files' },
    { to: '/feedbacks', icon: MessagesSquare, label: 'Feedback' },
    { to: '/about', icon: Info, label: 'About' },
  ];

  return (
    <div className="app-shell">
      <div className="topbar-mobile">
        <div className="nav-brand"><span className="dot" /> agent.console</div>
        <button className="btn btn-ghost" onClick={() => setMobileOpen((v) => !v)}><Menu size={18} /></button>
      </div>
      <nav className={`nav-rail ${mobileOpen ? 'open' : ''}`}>
        <div className="nav-brand"><Terminal size={17} /> agent.console</div>
        {links.map((l) => (
          <NavLink
            key={l.to}
            to={l.to}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            onClick={() => setMobileOpen(false)}
          >
            <l.icon size={16} /> {l.label}
          </NavLink>
        ))}
        <div className="nav-footer">
          <div style={{ marginBottom: 8 }}>{username}</div>
          <button className="nav-link" onClick={handleExit}>
            <LogOut size={15} /> Log out
          </button>
        </div>
      </nav>
      <main className="main-area">{children}</main>
    </div>
  );
}