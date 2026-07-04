import { useEffect, useRef, useState } from "react";
import { Upload, Search, ChevronLeft, ChevronRight, Check, X, Edit2, Trash2, Plus } from "lucide-react";
import clsx from "clsx";
import { api } from "../lib/api";
import Panel from "../components/Panel";

const TABS = ["Import", "Champions", "Players", "Teams", "Tournaments"];
const PAGE_SIZE = 30;
const BASE_URL = "http://localhost:8000/api";

async function apiFetch(path, opts = {}) {
  const res = await fetch(`${BASE_URL}${path}`, opts);
  return res.json();
}

// ── Inline edit cell ──────────────────────────────────────────────────────────
function EditCell({ value, onSave }) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(value ?? "");
  const inputRef = useRef();

  const start = () => { setEditing(true); setTimeout(() => inputRef.current?.focus(), 50); };
  const cancel = () => { setVal(value ?? ""); setEditing(false); };
  const save = () => { onSave(val); setEditing(false); };

  if (!editing) return (
    <div className="flex items-center gap-1.5 group cursor-pointer" onClick={start}>
      <span className="text-sm text-text">{value || "—"}</span>
      <Edit2 size={11} className="text-textMuted opacity-0 group-hover:opacity-100 transition-opacity" />
    </div>
  );

  return (
    <div className="flex items-center gap-1">
      <input
        ref={inputRef}
        value={val}
        onChange={(e) => setVal(e.target.value)}
        onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") cancel(); }}
        className="bg-bg border border-accent rounded px-2 py-0.5 text-sm text-text focus:outline-none w-32"
      />
      <button onClick={save} className="text-win hover:opacity-80"><Check size={14} /></button>
      <button onClick={cancel} className="text-loss hover:opacity-80"><X size={14} /></button>
    </div>
  );
}

// ── Add form modal ────────────────────────────────────────────────────────────
function AddModal({ fields, onSave, onClose }) {
  const [form, setForm] = useState({});
  const [loading, setLoading] = useState(false);

  const handle = async () => {
    setLoading(true);
    await onSave(form);
    setLoading(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-surface border border-border rounded-xl p-6 w-full max-w-md shadow-xl">
        <h3 className="font-display font-semibold text-text mb-4">Thêm mới</h3>
        <div className="space-y-3 mb-5">
          {fields.map((f) => (
            <div key={f.key}>
              <label className="text-xs text-textMuted uppercase tracking-wider block mb-1">{f.label}{f.required && " *"}</label>
              <input
                type={f.type ?? "text"}
                value={form[f.key] ?? ""}
                onChange={(e) => setForm((p) => ({ ...p, [f.key]: e.target.value }))}
                className="w-full bg-bg border border-border rounded-lg px-3 py-2 text-sm text-text focus:outline-none focus:border-accent"
                placeholder={f.placeholder ?? ""}
              />
            </div>
          ))}
        </div>
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-textMuted hover:text-text transition-colors">Hủy</button>
          <button
            onClick={handle}
            disabled={loading}
            className="px-4 py-2 text-sm bg-accent text-white rounded-lg hover:bg-accent/80 transition-colors disabled:opacity-50"
          >
            {loading ? "Đang lưu..." : "Lưu"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Delete confirm ────────────────────────────────────────────────────────────
function DeleteConfirm({ label, onConfirm, onClose }) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="bg-surface border border-border rounded-xl p-6 w-full max-w-sm shadow-xl">
        <h3 className="font-display font-semibold text-text mb-2">Xác nhận xóa</h3>
        <p className="text-sm text-textMuted mb-5">Xóa <span className="text-text font-medium">{label}</span>? Hành động này không thể hoàn tác.</p>
        <div className="flex gap-2 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-textMuted hover:text-text transition-colors">Hủy</button>
          <button onClick={onConfirm} className="px-4 py-2 text-sm bg-loss text-white rounded-lg hover:bg-loss/80 transition-colors">Xóa</button>
        </div>
      </div>
    </div>
  );
}

// ── Import tab ────────────────────────────────────────────────────────────────
function ImportTab() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const fileRef = useRef();

  const handleFile = async (f) => {
    setFile(f); setPreview(null); setResult(null); setError(null); setLoading(true);
    try {
      const data = await api.admin.previewImport(f);
      if (data.detail) throw new Error(JSON.stringify(data.detail));
      setPreview(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const handleImport = async () => {
    if (!file) return;
    setLoading(true); setError(null);
    try {
      const data = await api.admin.import(file);
      setResult(data);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h2 className="font-display font-semibold text-base text-text mb-1">Import Excel</h2>
        <p className="text-xs text-textMuted">Upload file Excel đúng format (sheet: LolMatchHistory_2020-2025). ETL dùng get_or_create — data đã có sẽ không bị duplicate.</p>
      </div>
      <div
        onClick={() => fileRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
        className="border-2 border-dashed border-border rounded-xl px-8 py-12 text-center cursor-pointer hover:border-accent transition-colors"
      >
        <Upload size={28} className="mx-auto text-textMuted mb-3" />
        <p className="text-sm text-text">{file ? file.name : "Kéo thả file vào đây hoặc click để chọn"}</p>
        <p className="text-xs text-textMuted mt-1">.xlsx hoặc .xls</p>
        <input ref={fileRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={(e) => { const f = e.target.files[0]; if (f) handleFile(f); }} />
      </div>
      {loading && <div className="text-sm text-textMuted animate-pulse">Đang xử lý...</div>}
      {error && <div className="text-sm text-loss bg-loss/10 border border-loss/30 rounded-lg px-4 py-3">{error}</div>}
      {preview && !result && (
        <Panel title="Preview">
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div className="bg-bg rounded-lg px-4 py-3">
              <div className="text-xs text-textMuted mb-1">Rows trong file</div>
              <div className="font-display font-bold text-2xl text-text">{preview.total_rows_in_file}</div>
            </div>
            <div className="bg-bg rounded-lg px-4 py-3">
              <div className="text-xs text-textMuted mb-1">Games đang có trong DB</div>
              <div className="font-display font-bold text-2xl text-text">{preview.existing_games_in_db}</div>
            </div>
          </div>
          <div className="mb-4 overflow-x-auto">
            <div className="text-xs text-textMuted uppercase tracking-wider mb-2">5 rows đầu tiên</div>
            <table className="w-full text-xs">
              <thead><tr className="border-b border-border">{Object.keys(preview.sample_rows[0] ?? {}).map((k) => <th key={k} className="text-left text-textMuted pb-2 pr-4 font-medium whitespace-nowrap">{k}</th>)}</tr></thead>
              <tbody>{preview.sample_rows.map((row, i) => <tr key={i} className="border-b border-border/50">{Object.values(row).map((v, j) => <td key={j} className="py-2 pr-4 text-text whitespace-nowrap">{String(v ?? "—")}</td>)}</tr>)}</tbody>
            </table>
          </div>
          <button onClick={handleImport} disabled={loading} className="bg-accent hover:bg-accent/80 text-white px-5 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50">Xác nhận Import</button>
        </Panel>
      )}
      {result && (
        <Panel title="Kết quả import">
          {result.status === "success" ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-win text-sm font-medium"><Check size={16} /> Import thành công</div>
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-bg rounded-lg px-4 py-3"><div className="text-xs text-textMuted mb-1">Games mới thêm</div><div className="font-display font-bold text-2xl text-win">{result.new_games}</div></div>
                <div className="bg-bg rounded-lg px-4 py-3"><div className="text-xs text-textMuted mb-1">Players mới thêm</div><div className="font-display font-bold text-2xl text-text">{result.new_players}</div></div>
              </div>
              <p className="text-xs text-textMuted">Tổng: {result.games_before} → {result.games_after} games trong DB.</p>
              <button onClick={() => { setFile(null); setPreview(null); setResult(null); }} className="text-xs text-accent hover:underline">Import file khác</button>
            </div>
          ) : <div className="text-sm text-loss">{result.detail ?? "Có lỗi xảy ra"}</div>}
        </Panel>
      )}
    </div>
  );
}

// ── Generic master data table ─────────────────────────────────────────────────
function MasterTable({ fetchFn, columns, updateFn, deleteFn, createFn, createFields, nameKey }) {
  const [data, setData] = useState([]);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  const load = (s = search, p = page) => {
    setLoading(true);
    fetchFn({ search: s, page: p, pageSize: PAGE_SIZE })
      .then((res) => setData(Array.isArray(res) ? res : (res.data ?? [])))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page]);

  const handleSearch = (val) => { setSearch(val); setPage(1); load(val, 1); };
  const handleUpdate = async (id, field, value) => { if (!updateFn) return; await updateFn(id, { [field]: value }); load(); };
  const handleDelete = async () => {
    if (!deleteTarget || !deleteFn) return;
    try {
      const res = await deleteFn(deleteTarget.id);
      if (res?.detail) throw new Error(typeof res.detail === "string" ? res.detail : JSON.stringify(res.detail));
      setDeleteTarget(null);
      load();
    } catch (e) {
      setDeleteTarget(null);
      setErrorMsg(e.message);
    }
  };
  const handleCreate = async (form) => {
    if (!createFn) return;
    try {
      const res = await createFn(form);
      if (res?.detail) throw new Error(typeof res.detail === "string" ? res.detail : JSON.stringify(res.detail));
      load();
    } catch (e) {
      setErrorMsg(e.message);
    }
  };

  const idKey = columns[0].key;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-surface border border-border rounded-lg px-3 py-2 flex-1 max-w-xs">
          <Search size={14} className="text-textMuted" />
          <input value={search} onChange={(e) => handleSearch(e.target.value)} placeholder="Tìm kiếm..." className="bg-transparent text-sm text-text placeholder:text-textMuted focus:outline-none flex-1" />
        </div>
        <span className="text-xs text-textMuted flex-1">{data.length} records (trang {page})</span>
        {createFn && (
          <button onClick={() => setShowAdd(true)} className="flex items-center gap-1.5 px-3 py-2 bg-accent text-white rounded-lg text-sm hover:bg-accent/80 transition-colors">
            <Plus size={14} /> Thêm mới
          </button>
        )}
      </div>

      {errorMsg && (
        <div className="flex items-center justify-between bg-loss/10 border border-loss/30 rounded-lg px-4 py-3">
          <span className="text-sm text-loss">{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-loss hover:opacity-70">
            <X size={14} />
          </button>
        </div>
      )}

      <div className="overflow-x-auto border border-border rounded-lg">
        <table className="w-full text-sm">
          <thead className="bg-surface">
            <tr className="border-b border-border">
              {columns.map((col) => <th key={col.key} className="text-left text-xs text-textMuted uppercase tracking-wider px-4 py-3 font-medium whitespace-nowrap">{col.label}</th>)}
              <th className="text-left text-xs text-textMuted uppercase tracking-wider px-4 py-3 font-medium">Hành động</th>
            </tr>
          </thead>
          <tbody>
            {loading
              ? [...Array(8)].map((_, i) => (
                  <tr key={i} className="border-b border-border/50">
                    {[...columns, { key: "_action" }].map((col) => <td key={col.key} className="px-4 py-3"><div className="h-4 bg-surfaceHover rounded animate-pulse w-20" /></td>)}
                  </tr>
                ))
              : data.map((row) => (
                  <tr key={row[idKey]} className="border-b border-border/50 hover:bg-surfaceHover/30 transition-colors">
                    {columns.map((col) => (
                      <td key={col.key} className="px-4 py-3">
                        {col.editable && updateFn
                          ? <EditCell value={row[col.key]} onSave={(val) => handleUpdate(row[idKey], col.key, val)} />
                          : <span className="text-text">{row[col.key] ?? "—"}</span>
                        }
                      </td>
                    ))}
                    <td className="px-4 py-3">
                      {deleteFn && (
                        <button
                          onClick={() => setDeleteTarget({ id: row[idKey], label: row[nameKey] ?? row[idKey] })}
                          className="text-textMuted hover:text-loss transition-colors"
                          title="Xóa"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))
            }
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-textMuted hover:text-text disabled:opacity-30 transition-colors">
          <ChevronLeft size={16} /> Trước
        </button>
        <span className="text-xs text-textMuted font-mono">Trang {page}</span>
        <button onClick={() => setPage((p) => p + 1)} disabled={data.length < PAGE_SIZE} className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-textMuted hover:text-text disabled:opacity-30 transition-colors">
          Sau <ChevronRight size={16} />
        </button>
      </div>

      {showAdd && createFields && (
        <AddModal fields={createFields} onSave={handleCreate} onClose={() => setShowAdd(false)} />
      )}
      {deleteTarget && (
        <DeleteConfirm label={deleteTarget.label} onConfirm={handleDelete} onClose={() => setDeleteTarget(null)} />
      )}
    </div>
  );
}

// ── Tab configs ───────────────────────────────────────────────────────────────
const TAB_CONFIGS = {
  Champions: {
    fetchFn: (p) => api.admin.champions(p),
    updateFn: (id, body) => api.admin.updateChampion(id, body),
    deleteFn: (id) => apiFetch(`/admin/champions/${id}`, { method: "DELETE" }),
    createFn: (body) => apiFetch("/admin/champions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
    nameKey: "name",
    createFields: [
      { key: "name", label: "Tên champion", required: true },
      { key: "image_url", label: "Image URL" },
    ],
    columns: [
      { key: "id_champion", label: "ID" },
      { key: "name", label: "Tên", editable: true },
      { key: "image_url", label: "Image URL", editable: true },
    ],
  },
  Players: {
    fetchFn: (p) => api.admin.players(p),
    updateFn: (id, body) => api.admin.updatePlayer(id, body),
    deleteFn: (id) => apiFetch(`/admin/players/${id}`, { method: "DELETE" }),
    createFn: (body) => apiFetch("/admin/players", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
    nameKey: "ingame_name",
    createFields: [
      { key: "ingame_name", label: "Nickname", required: true },
      { key: "full_name", label: "Họ tên" },
      { key: "position", label: "Role (TOP/JUNGLER/MID/ADC/SUPPORT)" },
      { key: "country", label: "Quốc gia" },
      { key: "team_id", label: "Team ID", type: "number" },
    ],
    columns: [
      { key: "id_player", label: "ID" },
      { key: "ingame_name", label: "Nickname", editable: true },
      { key: "full_name", label: "Họ tên", editable: true },
      { key: "position", label: "Role", editable: true },
      { key: "country", label: "Quốc gia", editable: true },
      { key: "team_name", label: "Team" },
    ],
  },
  Teams: {
    fetchFn: (p) => api.admin.teams(p),
    deleteFn: (id) => apiFetch(`/admin/teams/${id}`, { method: "DELETE" }),
    createFn: (body) => apiFetch("/admin/teams", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
    nameKey: "name",
    createFields: [
      { key: "name", label: "Tên team", required: true },
      { key: "region", label: "Region (KR/INT/...)" },
    ],
    columns: [
      { key: "id_team", label: "ID" },
      { key: "name", label: "Tên" },
      { key: "region", label: "Region" },
    ],
  },
  Tournaments: {
    fetchFn: (p) => api.admin.tournaments(p),
    deleteFn: (id) => apiFetch(`/admin/tournaments/${id}`, { method: "DELETE" }),
    createFn: (body) => apiFetch("/admin/tournaments", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...body, year: Number(body.year) }) }),
    nameKey: "name",
    createFields: [
      { key: "name", label: "Tên giải đấu", required: true },
      { key: "year", label: "Năm", type: "number", required: true },
      { key: "region", label: "Region (KR/INT)" },
      { key: "ist1winner", label: "T1 vô địch? (YES/NO)" },
      { key: "winner", label: "Đội vô địch" },
    ],
    columns: [
      { key: "id_tournament", label: "ID" },
      { key: "name", label: "Tên" },
      { key: "year", label: "Năm" },
      { key: "region", label: "Region" },
      { key: "ist1winner", label: "T1 vô địch?" },
      { key: "winner", label: "Vô địch" },
    ],
  },
};

// ── Main ──────────────────────────────────────────────────────────────────────
export default function Admin() {
  const [activeTab, setActiveTab] = useState("Import");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display font-bold text-2xl text-text">Admin</h1>
        <p className="text-textMuted text-sm mt-1">Import data từ Excel và quản lý master data.</p>
      </div>
      <div className="flex gap-1 border-b border-border">
        {TABS.map((tab) => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={clsx("px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px", activeTab === tab ? "border-accent text-accent" : "border-transparent text-textMuted hover:text-text")}>
            {tab}
          </button>
        ))}
      </div>
      <div>
        {activeTab === "Import" && <ImportTab />}
        {activeTab !== "Import" && TAB_CONFIGS[activeTab] && <MasterTable key={activeTab} {...TAB_CONFIGS[activeTab]} />}
      </div>
    </div>
  );
}