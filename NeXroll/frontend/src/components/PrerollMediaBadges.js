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
// audio won't pass an ARC / Dolby Digital-only chain. onConvert adds a one-click fix.
export default function PrerollMediaBadges({ preroll, onConvert, converting = false }) {
  const badges = mediaBadges(preroll);
  if (!badges.length) return null;
  const flagged = preroll.audio_arc_ok === false;
  return (
    <div className="nx-media-badges" style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.15rem', margin: '0.25rem 0' }}>
      {badges.map(b => (
        <span key={b.key} style={pill(b.tone)} title={b.title || undefined}>
          {b.key === 'arc' && <AlertTriangle size={11} aria-hidden="true" />}
          {b.label}
        </span>
      ))}
      {flagged && onConvert && (
        <button
          type="button"
          className="button button-secondary"
          style={{ fontSize: '0.7rem', padding: '0.1rem 0.45rem' }}
          disabled={converting}
          title={`${ARC_WARNING}. Re-encode the audio to Dolby Digital Plus; the video is copied.`}
          onClick={(event) => { event.stopPropagation(); onConvert(preroll); }}
        >
          {converting ? 'Converting…' : 'Convert to DD+'}
        </button>
      )}
    </div>
  );
}

// Library filter chips: resolution, HDR and audio compatibility, plus "convert all flagged".
export function MediaFilterChips({ filters, onChange, prerolls, onConvertAll, converting = false, chipClass = 'nx-hybrid-filter-chip' }) {
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
      {onConvertAll && flaggedCount > 0 && (
        <button type="button" className={chipClass} disabled={converting} onClick={onConvertAll}
          title="Re-encode every flagged preroll's audio to Dolby Digital Plus (originals are kept unless turned off)">
          {converting ? 'Converting…' : 'Convert all flagged'}
        </button>
      )}
    </>
  );
}
