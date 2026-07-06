import {
  Terminal, ShieldCheck, KeyRound, FolderLock, Split, Ban,
  Link as LinkIcon, Mail, Sparkles, ListChecks,
} from 'lucide-react';

// ---- Edit this with your own details ----
const AUTHOR = {
  name: 'Ajay Sah',
  role: 'Creator & Maintainer',
  github: 'https://github.com/ajaysah-ai/',
  email: 'ajay.sah.aieng@gmail.com',
  linkedin: 'https://www.linkedin.com/in/ajaysah-ai/',
  bio: "Hello, I am Ajay Sah, a BCA graduate specializing in AI Engineering, Agentic AI, and Automation, with a keen research interest in Artificial General Intelligence (AGI). I developed the 'GitHub Automation Agent' to showcase practical expertise in autonomous agents and workflows. Moving forward, I plan to integrate an open-source, cost-free 'Image Generation' feature into this ecosystem.",
};

const TOOLS = [
  { name: 'write_readme', label: 'Write README', desc: 'Generates a README.md for a file or an entire project folder.' },
  { name: 'write_requirements', label: 'Write Requirements', desc: 'Scans a project and generates a requirements.txt / dependency file.' },
  { name: 'push_folder', label: 'Push Folder', desc: 'Pushes a local workspace folder to a GitHub repository.' },
  { name: 'pull_repo', label: 'Pull Repository', desc: 'Clones a GitHub repository into your workspace.' },
  { name: 'create_repo', label: 'Create Repository', desc: 'Creates a new GitHub repository (public or private).' },
  { name: 'delete_repo', label: 'Delete Repository', desc: 'Permanently deletes a repository you own.' },
  { name: 'list_repos', label: 'List Repositories', desc: 'Lists all repositories under your account.' },
  { name: 'list_repo_files', label: 'List Repo Files', desc: 'Lists files inside a specific repository or sub-folder.' },
];

const STEPS = [
  { title: 'Sign up', body: 'Signup takes your GitHub token and Groq API key once — they\'re never asked for again mid-task.' },
  { title: 'Describe your goal', body: 'Plain language: "create repo my-project" or "write a readme for my_project folder". The agent plans the exact steps.' },
  { title: 'Answer clarifications, if any', body: 'If a required detail is missing (like a repo name), the agent asks — up to 3 times — instead of guessing.' },
  { title: 'Review and approve the plan, once', body: 'Every proposed action + its parameters is shown together, git-diff style. One "yes" runs everything; anything else cancels the whole task.' },
  { title: 'Track it in History', body: 'Every goal, across every session, is saved and revisitable.' },
];

const SECURITY = [
  { icon: KeyRound, title: 'Encrypted credentials', body: 'Your GitHub token and Groq API key are encrypted (Fernet/AES) before they ever touch storage, and decrypted only in-memory when a task runs.' },
  { icon: ShieldCheck, title: 'Hashed passwords + JWT sessions', body: 'Passwords are bcrypt-hashed, never stored in plain text. Login issues a JWT that expires after 24 hours.' },
  { icon: FolderLock, title: 'Per-user workspace isolation', body: 'Every uploaded project lives under a path scoped to your account. Path-traversal and zip-slip attempts are detected and blocked automatically.' },
  { icon: Split, title: 'Plan review before execution', body: 'An independent reviewer step double-checks every plan against the goal before it\'s ever shown to you — nothing runs on a single, unchecked guess.' },
  { icon: Ban, title: 'No silent actions', body: 'Nothing executes without your explicit one-time approval of the full plan. Decline, and nothing runs at all.' },
];

export default function AboutPage() {
  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">About</h1>
        <p className="page-subtitle">What this agent does, how to use it, and how your data is handled.</p>
      </div>

      {/* Author */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 10, background: 'var(--accent-soft)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <Terminal size={20} color="var(--accent)" />
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1.05rem' }}>{AUTHOR.name}</div>
            <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem', marginBottom: 8 }}>{AUTHOR.role}</div>
            <p style={{ color: 'var(--text-dim)', fontSize: '0.88rem', margin: '0 0 10px' }}>{AUTHOR.bio}</p>
            <div style={{ display: 'flex', gap: 14 }}>
              {AUTHOR.github && <a href={AUTHOR.github} target="_blank" rel="noreferrer" className="nav-link" style={{ width: 'auto', padding: '4px 0' }}><LinkIcon size={15} /> GitHub</a>}
              {AUTHOR.email && <a href={`mailto:${AUTHOR.email}`} className="nav-link" style={{ width: 'auto', padding: '4px 0' }}><Mail size={15} /> Email</a>}
              {AUTHOR.linkedin && <a href={AUTHOR.linkedin} target="_blank" rel="noreferrer" className="nav-link" style={{ width: 'auto', padding: '4px 0' }}><LinkIcon size={15} /> LinkedIn</a>}
            </div>
          </div>
        </div>
      </div>

      {/* What it is */}
      <Section icon={Sparkles} title="What this is">
        <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', lineHeight: 1.6, margin: 0 }}>
          GitHub Automation Agent turns plain-language goals into planned, reviewed, and approved GitHub
          operations — creating and managing repositories, pushing and pulling code, and generating
          documentation — without writing the commands yourself. Every plan is machine-reviewed for
          correctness before you're asked to approve it, and nothing executes without that one explicit approval.
        </p>
      </Section>

      {/* Tools */}
      <Section icon={ListChecks} title="Available tools">
        <div className="list">
          {TOOLS.map((t) => (
            <div key={t.name} className="list-item" style={{ cursor: 'default' }}>
              <div className="list-item-main">
                <div className="list-item-title">{t.label}</div>
                <div className="list-item-sub">{t.desc}</div>
              </div>
              <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>{t.name}</span>
            </div>
          ))}
        </div>
      </Section>

      {/* How to use */}
      <Section icon={Terminal} title="How to use it">
        <div className="list">
          {STEPS.map((s, i) => (
            <div key={i} className="card" style={{ display: 'flex', gap: 14 }}>
              <div style={{
                fontFamily: 'var(--font-mono)', color: 'var(--accent)', fontWeight: 600,
                flexShrink: 0, width: 24,
              }}>{i + 1}</div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>{s.title}</div>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem', lineHeight: 1.55 }}>{s.body}</div>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* Security & privacy */}
      <Section icon={ShieldCheck} title="Security & privacy">
        <div className="list">
          {SECURITY.map((s, i) => (
            <div key={i} className="card" style={{ display: 'flex', gap: 14 }}>
              <div style={{
                width: 34, height: 34, borderRadius: 8, background: 'var(--ok-soft)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <s.icon size={16} color="var(--ok)" />
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: 4 }}>{s.title}</div>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.85rem', lineHeight: 1.55 }}>{s.body}</div>
              </div>
            </div>
          ))}
        </div>
      </Section>
    </div>
  );
}

function Section({ icon: Icon, title, children }) {
  return (
    <div style={{ marginBottom: 28 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Icon size={16} color="var(--accent)" />
        <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.05rem', margin: 0 }}>{title}</h2>
      </div>
      {children}
    </div>
  );
}