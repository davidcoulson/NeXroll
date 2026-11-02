// Media facts NeXroll reads from each preroll with ffprobe (resolution, HDR, audio),
// and the library filters built on them. Fields are null until a file has been probed.

export const ARC_WARNING = 'This audio may not pass an ARC / Dolby Digital-only chain';

const AUDIO_NAMES = {
  ac3: 'Dolby Digital',
  eac3: 'Dolby Digital Plus',
  truehd: 'TrueHD',
  dts: 'DTS',
  aac: 'AAC',
  flac: 'FLAC',
  mp3: 'MP3',
  opus: 'Opus',
};

export function channelLabel(channels) {
  if (!channels) return '';
  if (channels === 6) return '5.1';
  if (channels === 8) return '7.1';
  if (channels === 2) return '2.0';
  if (channels === 1) return '1.0';
  return `${channels}ch`;
}

export function audioLabel(preroll) {
  const codec = String(preroll?.audio_codec || '').toLowerCase();
  if (!codec) return '';
  const name = codec.startsWith('dts') ? AUDIO_NAMES.dts : (codec.startsWith('pcm') ? 'PCM' : (AUDIO_NAMES[codec] || codec.toUpperCase()));
  return `${name} ${channelLabel(preroll.audio_channels)}`.trim();
}

// [{key, label, tone}] in display order; empty when nothing is known yet.
export function mediaBadges(preroll) {
  const out = [];
  if (!preroll) return out;
  if (preroll.resolution === '2160p') out.push({ key: 'res', label: '4K', tone: 'info' });
  else if (preroll.resolution) out.push({ key: 'res', label: preroll.resolution, tone: 'neutral' });
  if (preroll.hdr_type === 'Dolby Vision') out.push({ key: 'hdr', label: 'Dolby Vision', tone: 'info' });
  else if (preroll.hdr_type === 'HDR10' || preroll.hdr_type === 'HLG') out.push({ key: 'hdr', label: preroll.hdr_type === 'HLG' ? 'HLG' : 'HDR', tone: 'info' });
  const audio = audioLabel(preroll);
  if (audio) out.push({ key: 'audio', label: audio, tone: preroll.audio_arc_ok === false ? 'warn' : 'neutral' });
  if (preroll.audio_arc_ok === false) out.push({ key: 'arc', label: 'Not ARC-safe', tone: 'warn', title: ARC_WARNING });
  return out;
}

// filters: { resolution: '' | '2160p' | ..., hdr: '' | 'any' | 'none', audio: '' | 'ok' | 'flagged' }
export function matchesMediaFilters(preroll, filters) {
  const { resolution = '', hdr = '', audio = '' } = filters || {};
  if (resolution && preroll.resolution !== resolution) return false;
  const isHdr = ['HDR10', 'HLG', 'Dolby Vision'].includes(preroll.hdr_type);
  if (hdr === 'any' && !isHdr) return false;
  if (hdr === 'none' && isHdr) return false;
  if (audio === 'flagged' && preroll.audio_arc_ok !== false) return false;
  if (audio === 'ok' && preroll.audio_arc_ok !== true) return false;
  return true;
}

export const hasMediaFilters = (filters) => Boolean(filters && (filters.resolution || filters.hdr || filters.audio));
