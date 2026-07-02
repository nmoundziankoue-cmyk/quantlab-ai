import { useState } from "react";
import { useProjects, useCreateProject, useNotes, useCreateNote, useBookmarks, useCreateBookmark, useRecentActivity, usePinnedItems } from "../hooks/useResearchWorkspace";
import useWorkspaceStore from "../store/useWorkspaceStore";

const S = {
  page: { display: "flex", height: "100vh", background: "#0d1117", color: "#e6edf3" },
  sidebar: { width: 240, background: "#161b22", borderRight: "1px solid #30363d", padding: 16, overflowY: "auto" },
  main: { flex: 1, padding: 24, overflowY: "auto" },
  sideTitle: { fontSize: 11, color: "#8b949e", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 },
  navItem: (active) => ({ padding: "8px 12px", borderRadius: 6, cursor: "pointer", fontSize: 13, marginBottom: 2, background: active ? "#21262d" : "transparent", color: active ? "#e6edf3" : "#8b949e" }),
  card: { background: "#161b22", border: "1px solid #30363d", borderRadius: 8, padding: 20, marginBottom: 16 },
  cardTitle: { fontSize: 13, color: "#8b949e", fontWeight: 600, marginBottom: 12, textTransform: "uppercase", letterSpacing: "0.05em" },
  input: { background: "#0d1117", border: "1px solid #30363d", borderRadius: 6, padding: "8px 12px", color: "#e6edf3", fontSize: 13, width: "100%", outline: "none" },
  btn: (color = "#238636") => ({ background: color, border: "none", borderRadius: 6, padding: "8px 16px", color: "#fff", cursor: "pointer", fontSize: 13, fontWeight: 600 }),
  row: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #21262d" },
  tag: { background: "#1c2128", borderRadius: 4, padding: "2px 8px", fontSize: 11, color: "#8b949e" },
};

function ProjectList() {
  const { data: projects = [] } = useProjects();
  const createProject = useCreateProject();
  const [newName, setNewName] = useState("");
  const { setActiveProjectId } = useWorkspaceStore();

  return (
    <div style={S.card}>
      <div style={S.cardTitle}>Projects ({projects.length})</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input style={S.input} placeholder="Project name..." value={newName} onChange={(e) => setNewName(e.target.value)} />
        <button style={S.btn()} onClick={() => { if (newName.trim()) { createProject.mutate({ name: newName }); setNewName(""); } }}>Add</button>
      </div>
      {projects.map((p) => (
        <div key={p.id} style={{ ...S.row, cursor: "pointer" }} onClick={() => setActiveProjectId(p.id)}>
          <span style={{ fontSize: 14 }}>{p.name}</span>
          <span style={S.tag}>{p.status}</span>
        </div>
      ))}
    </div>
  );
}

function NoteList() {
  const { activeProjectId } = useWorkspaceStore();
  const { data: notes = [] } = useNotes(activeProjectId);
  const createNote = useCreateNote();
  const [title, setTitle] = useState("");

  if (!activeProjectId) return <div style={{ color: "#8b949e", fontSize: 13 }}>Select a project to view notes</div>;

  return (
    <div style={S.card}>
      <div style={S.cardTitle}>Notes ({notes.length})</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <input style={S.input} placeholder="Note title..." value={title} onChange={(e) => setTitle(e.target.value)} />
        <button style={S.btn()} onClick={() => { if (title.trim()) { createNote.mutate({ project_id: activeProjectId, title }); setTitle(""); } }}>Add</button>
      </div>
      {notes.map((n) => (
        <div key={n.id} style={S.row}>
          <span style={{ fontSize: 14 }}>{n.title}</span>
          {n.is_pinned && <span style={{ color: "#f0883e", fontSize: 11 }}>📌</span>}
        </div>
      ))}
    </div>
  );
}

function BookmarkList() {
  const { data: bookmarks = [] } = useBookmarks();
  const createBookmark = useCreateBookmark();
  const [bTitle, setBTitle] = useState("");
  const [bUrl, setBUrl] = useState("");

  return (
    <div style={S.card}>
      <div style={S.cardTitle}>Bookmarks ({bookmarks.length})</div>
      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <input style={{ ...S.input, width: 160 }} placeholder="Title" value={bTitle} onChange={(e) => setBTitle(e.target.value)} />
        <input style={{ ...S.input, width: 220 }} placeholder="URL (optional)" value={bUrl} onChange={(e) => setBUrl(e.target.value)} />
        <button style={S.btn()} onClick={() => { if (bTitle.trim()) { createBookmark.mutate({ title: bTitle, url: bUrl || undefined }); setBTitle(""); setBUrl(""); } }}>Save</button>
      </div>
      {bookmarks.map((b) => (
        <div key={b.id} style={S.row}>
          <span style={{ fontSize: 14 }}>{b.title}</span>
          {b.url && <a href={b.url} target="_blank" rel="noreferrer" style={{ fontSize: 11, color: "#58a6ff" }}>↗</a>}
        </div>
      ))}
    </div>
  );
}

export default function ResearchWorkspace() {
  const { activeTab, setActiveTab } = useWorkspaceStore();
  const { data: activity = [] } = useRecentActivity(6);
  const { data: pinned = [] } = usePinnedItems();

  const tabs = ["projects", "notes", "bookmarks", "pinned", "activity"];

  return (
    <div style={S.page}>
      <div style={S.sidebar}>
        <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 20, color: "#e6edf3" }}>Workspace</div>
        {tabs.map((t) => (
          <div key={t} style={S.navItem(activeTab === t)} onClick={() => setActiveTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </div>
        ))}
      </div>
      <div style={S.main}>
        {activeTab === "projects" && <ProjectList />}
        {activeTab === "notes" && <NoteList />}
        {activeTab === "bookmarks" && <BookmarkList />}
        {activeTab === "pinned" && (
          <div style={S.card}>
            <div style={S.cardTitle}>Pinned Items ({pinned.length})</div>
            {pinned.map((p) => (
              <div key={p.id} style={S.row}>
                <span style={{ fontSize: 14 }}>{p.label}</span>
                <span style={{ ...S.tag }}>{p.entity_type}</span>
              </div>
            ))}
          </div>
        )}
        {activeTab === "activity" && (
          <div style={S.card}>
            <div style={S.cardTitle}>Recent Activity</div>
            {activity.map((a, i) => (
              <div key={i} style={S.row}>
                <span style={{ fontSize: 13 }}>{a.description}</span>
                <span style={S.tag}>{a.activity_type}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
