import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Plus, Trash2, Edit, Save, X } from 'lucide-react';

const EMPTY = {
  id: null, name: '', enabled: true, priority: 0, match: 'all',
  min_resolution: '', hdr: false, atmos: false, genres: '', content_ratings: '', title_contains: '',
  action_type: 'category', action_id: '',
};

const toForm = (rule) => ({
  id: rule.id, name: rule.name, enabled: rule.enabled, priority: rule.priority, match: rule.match,
  min_resolution: rule.conditions.min_resolution || '',
  hdr: Boolean(rule.conditions.hdr),
  atmos: Boolean(rule.conditions.atmos),
  genres: (rule.conditions.genres || []).join(', '),
  content_ratings: (rule.conditions.content_ratings || []).join(', '),
  title_contains: rule.conditions.title_contains || '',
  action_type: rule.action.type, action_id: String(rule.action.id),
});

const toPayload = (f) => ({
  name: f.name,
  enabled: f.enabled,
  priority: Number(f.priority) || 0,
  match: f.match,
  conditions: {
    min_resolution: f.min_resolution || undefined,
    hdr: f.hdr || undefined,
    atmos: f.atmos || undefined,
    genres: f.genres.split(',').map(s => s.trim()).filter(Boolean),
    content_ratings: f.content_ratings.split(',').map(s => s.trim()).filter(Boolean),
    title_contains: f.title_contains.trim() || undefined,
  },
  action_type: f.action_type,
  action_id: Number(f.action_id),
});

export function describeConditions(c) {
  const parts = [];
  if (c.min_resolution) parts.push(`resolution ≥ ${c.min_resolution}`);
  if (c.hdr) parts.push('HDR');
  if (c.atmos) parts.push('Dolby Atmos');
  if (c.genres?.length) parts.push(`genre: ${c.genres.join(', ')}`);
  if (c.content_ratings?.length) parts.push(`rated: ${c.content_ratings.join(', ')}`);
  if (c.title_contains) parts.push(`title contains "${c.title_contains}"`);
  return parts;
}

// Film rules: pick a category or sequence by the film that is about to play.
// Applied on Jellyfin/Emby; Plex callers use POST /rules/evaluate.
export default function FilmRulesPanel({ apiUrl, categories = [], sequences = [], showAlert }) {
  const [rules, setRules] = useState([]);
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  // App re-creates showAlert every render; keep load() stable so the effect runs once.
  const alertRef = useRef(showAlert);
  alertRef.current = showAlert;

  const load = useCallback(async () => {
    try {
      const res = await fetch(apiUrl('rules'));
      const data = await res.json();
      setRules(Array.isArray(data) ? data : []);
    } catch (e) {
      alertRef.current(`Could not load film rules: ${e?.message || e}`, 'error');
    }
  }, [apiUrl]);

  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      const res = await fetch(apiUrl(form.id ? `rules/${form.id}` : 'rules'), {
        method: form.id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(toPayload(form)),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) { showAlert(typeof data.detail === 'string' ? data.detail : 'Could not save the rule', 'error'); return; }
      setForm(null);
      load();
    } catch (e) {
      showAlert(`Could not save the rule: ${e?.message || e}`, 'error');
    } finally {
      setSaving(false);
    }
  };

  const toggle = async (rule) => {
    const f = { ...toForm(rule), enabled: !rule.enabled };
    await fetch(apiUrl(`rules/${rule.id}`), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(toPayload(f)) });
    load();
  };

  const remove = async (rule) => {
    await fetch(apiUrl(`rules/${rule.id}`), { method: 'DELETE' });
    load();
  };

  const set = (patch) => setForm(prev => ({ ...prev, ...patch }));
  const targets = form && form.action_type === 'sequence' ? sequences : categories;

  return (
    <div className="nx-film-rules" style={{ display: 'grid', gap: '1rem' }}>
      <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
        A rule picks a category or sequence by the film that is about to play. Rules run before schedules, highest
        priority first, and the first match wins. NeXroll can see the film on Jellyfin and Emby; for Plex, send the
        film to <code>POST /rules/evaluate</code>.
      </p>
      {!form && (
        <div><button type="button" className="button" onClick={() => setForm({ ...EMPTY })}><Plus size={15} /> New rule</button></div>
      )}
      {form && (
        <div className="card" style={{ display: 'grid', gap: '0.6rem', padding: '1rem' }}>
          <input className="input" placeholder="Rule name" value={form.name} onChange={e => set({ name: e.target.value })} />
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <label>Priority <input className="input" type="number" style={{ width: '5rem' }} value={form.priority} onChange={e => set({ priority: e.target.value })} /></label>
            <label>Match <select className="input" value={form.match} onChange={e => set({ match: e.target.value })}>
              <option value="all">all conditions</option><option value="any">any condition</option></select></label>
            <label><input type="checkbox" checked={form.enabled} onChange={e => set({ enabled: e.target.checked })} /> Enabled</label>
          </div>
          <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <label>Resolution at least <select className="input" value={form.min_resolution} onChange={e => set({ min_resolution: e.target.value })}>
              <option value="">any</option><option value="720p">720p</option><option value="1080p">1080p</option><option value="2160p">4K (2160p)</option></select></label>
            <label><input type="checkbox" checked={form.hdr} onChange={e => set({ hdr: e.target.checked })} /> HDR</label>
            <label><input type="checkbox" checked={form.atmos} onChange={e => set({ atmos: e.target.checked })} /> Dolby Atmos</label>
          </div>
          <input className="input" placeholder="Genres (comma separated)" value={form.genres} onChange={e => set({ genres: e.target.value })} />
          <input className="input" placeholder="Content ratings (e.g. R, PG-13)" value={form.content_ratings} onChange={e => set({ content_ratings: e.target.value })} />
          <input className="input" placeholder="Title contains" value={form.title_contains} onChange={e => set({ title_contains: e.target.value })} />
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
            <label>Then use <select className="input" value={form.action_type} onChange={e => set({ action_type: e.target.value, action_id: '' })}>
              <option value="category">category</option><option value="sequence">sequence</option></select></label>
            <select className="input" value={form.action_id} onChange={e => set({ action_id: e.target.value })} aria-label="Target">
              <option value="">Choose…</option>
              {targets.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button type="button" className="button" disabled={saving || !form.name.trim() || !form.action_id} onClick={save}><Save size={15} /> Save rule</button>
            <button type="button" className="button button-secondary" onClick={() => setForm(null)}><X size={15} /> Cancel</button>
          </div>
        </div>
      )}
      {rules.length === 0 && !form && <p style={{ color: 'var(--text-secondary)' }}>No film rules yet.</p>}
      {rules.map(rule => (
        <div key={rule.id} className="card" style={{ display: 'flex', gap: '1rem', alignItems: 'center', padding: '0.75rem 1rem', opacity: rule.enabled ? 1 : 0.6 }}>
          <input type="checkbox" checked={rule.enabled} onChange={() => toggle(rule)} aria-label={`Enable ${rule.name}`} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <strong>{rule.name}</strong> <span style={{ color: 'var(--text-secondary)', fontSize: '0.8rem' }}>priority {rule.priority}</span>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              {describeConditions(rule.conditions).join(rule.match === 'any' ? ' or ' : ' and ')} &rarr; {rule.action.type}{' '}
              {rule.action.missing ? <em>(deleted)</em> : <strong>{rule.action.name}</strong>}
            </div>
          </div>
          <button type="button" className="nx-iconbtn" title="Edit" onClick={() => setForm(toForm(rule))}><Edit size={15} /></button>
          <button type="button" className="nx-iconbtn" title="Delete" onClick={() => remove(rule)}><Trash2 size={15} /></button>
        </div>
      ))}
    </div>
  );
}
