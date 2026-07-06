import { useState, useEffect, useRef } from 'react';
import { UploadCloud, Download, Trash2, FolderGit2 } from 'lucide-react';
import { useAuth } from '../context/Authcontext.jsx';
import { useToast } from '../context/Toastcontext.jsx';
import { api, ApiError, BASE_URL } from '../api/client.js';

export default function FilesPage() {
  const { token } = useAuth();
  const { showToast } = useToast();
  const [projects, setProjects] = useState(null);
  const [projectName, setProjectName] = useState('');
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  async function refresh() {
    try {
      const res = await api.listFiles(token);
      setProjects(res.projects);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not load files.');
    }
  }

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, []);

  async function handleFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setError('Only .zip files are accepted.');
      return;
    }
    const name = projectName.trim() || file.name.replace(/\.zip$/i, '');
    setBusy(true);
    setError('');
    try {
      const res = await api.uploadFile(token, name, file);
      if (res.skipped_unsafe_entries?.length) {
        showToast(`Uploaded, but ${res.skipped_unsafe_entries.length} unsafe entr${res.skipped_unsafe_entries.length === 1 ? 'y was' : 'ies were'} skipped`, 'danger');
      } else {
        showToast('Project uploaded', 'ok');
      }
      setProjectName('');
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Upload failed.');
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete(name) {
    if (!window.confirm(`Delete "${name}"? This cannot be undone.`)) return;
    try {
      await api.deleteFile(token, name);
      showToast('Deleted', 'ok');
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Delete failed.');
    }
  }

  async function handleDownload(name) {
    // A plain <a href> can't attach an Authorization header, and this endpoint
    // is JWT-protected — so fetch it manually and trigger the save via a blob URL.
    try {
      const res = await fetch(`${BASE_URL}/files/download/${encodeURIComponent(name)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Download failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${name}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      showToast(err.message || 'Download failed', 'danger');
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1 className="page-title">Files</h1>
        <p className="page-subtitle">Upload a project as a .zip — it becomes available to the agent as a workspace folder.</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="field">
        <label className="label">Project name (optional — defaults to zip filename)</label>
        <input className="input" value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder="my_project" />
      </div>

      <div
        className={`dropzone ${dragging ? 'drag' : ''}`}
        onClick={() => fileInputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
      >
        {busy ? <span className="spinner" /> : (
          <>
            <UploadCloud size={22} style={{ marginBottom: 8 }} />
            <div>Drag a .zip here, or click to browse (max 50MB)</div>
          </>
        )}
        <input ref={fileInputRef} type="file" accept=".zip" hidden onChange={(e) => handleFile(e.target.files[0])} />
      </div>

      <div style={{ marginTop: 24 }}>
        {projects === null && <div className="spinner" />}
        {projects && projects.length === 0 && (
          <div className="empty-state">
            <div className="icon"><FolderGit2 size={28} /></div>
            <p>No projects uploaded yet.</p>
          </div>
        )}
        {projects && projects.length > 0 && (
          <div className="list">
            {projects.map((name) => (
              <div key={name} className="list-item" style={{ cursor: 'default' }}>
                <div className="list-item-main">
                  <div className="list-item-title">{name}</div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn btn-ghost" onClick={() => handleDownload(name)}><Download size={15} /></button>
                  <button className="btn btn-ghost" onClick={() => handleDelete(name)}><Trash2 size={15} /></button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}