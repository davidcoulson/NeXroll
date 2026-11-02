import React from 'react';
import { AlertTriangle } from 'lucide-react';
import { mediaBadges, ARC_WARNING } from '../utils/mediaBadges';

const TONES = {
  info: { color: 'var(--text-color)', background: 'color-mix(in srgb, var(--nx-sec-connect) 18%, transparent)' },
  neutral: { color: 'var(--text-secondary)', background: 'color-mix(in srgb, var(--text-secondary) 12%, transparent)' },
  warn: { color: 'var(--text-color)', background: 'color-mix(in srgb, var(--warning-color, #f59e0b) 22%, transparent)' },
};

const pill = (tone) => ({
  display: 'inline-flex',
  alignItems: 'center',
  gap: '0.2rem',
  fontSize: '0.7rem',
  fontWeight: 600,
  padding: '0.1rem 0.4rem',
  borderRadius: '4px',
  marginRight: '0.25rem',
  ...TONES[tone],
});

// Small badge row: 4K / HDR / Dolby Vision / audio codec + channels, and a warning when the
// audio won't pass an ARC / Dolby Digital-only chain.
export default function PrerollMediaBadges({ preroll }) {
  const badges = mediaBadges(preroll);
  if (!badges.length) return null;
  return (
    <div className="nx-media-badges" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.15rem', margin: '0.25rem 0' }}>
      {badges.map(b => (
        <span key={b.key} style={pill(b.tone)} title={b.title || undefined}>
          {b.key === 'arc' && <AlertTriangle size={11} aria-hidden="true" />}
          {b.label}
        </span>
      ))}
    </div>
  );
}

// Library filter chips: resolution, HDR and audio compatibility
export function MediaFilterChips({ filters, onChange, prerolls, chipClass = 'nx-hybrid-filter-chip' }) {
  const flaggedCount = prerolls.filter(p => p.audio_arc_ok === false).length;
  const toggle = (key, value) => onChange({ ...filters, [key]: filters[key] === value ? '' : value });
  const chip = (key, value, label, title) => (
    <button
      type="button"
      key={`${key}-${value}`}
      className={`${chipClass}${filters[key] === value ? ' is-active' : ''}`}
      title={title}
      onClick={() => toggle(key, value)}
    >
      {label}
    </button>
  );
  return (
    <>
      {chip('resolution', '2160p', '4K')}
      {chip('resolution', '1080p', '1080p')}
      {chip('hdr', 'any', 'HDR / Dolby Vision')}
      {chip('audio', 'flagged', `Not ARC-safe · ${flaggedCount}`, ARC_WARNING)}
    </>
  );
}
