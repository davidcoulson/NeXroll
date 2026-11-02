import { mediaBadges, matchesMediaFilters, audioLabel } from './mediaBadges';

describe('mediaBadges', () => {
  test('4K Dolby Vision with TrueHD is flagged', () => {
    const labels = mediaBadges({ resolution: '2160p', hdr_type: 'Dolby Vision', audio_codec: 'truehd', audio_channels: 8, audio_arc_ok: false });
    expect(labels.map(b => b.label)).toEqual(['4K', 'Dolby Vision', 'TrueHD 7.1', 'Not ARC-safe']);
  });

  test('SDR stereo AAC has no warning', () => {
    const labels = mediaBadges({ resolution: '1080p', hdr_type: 'SDR', audio_codec: 'aac', audio_channels: 2, audio_arc_ok: true });
    expect(labels.map(b => b.label)).toEqual(['1080p', 'AAC 2.0']);
  });

  test('unprobed prerolls show nothing', () => {
    expect(mediaBadges({})).toEqual([]);
    expect(audioLabel({})).toBe('');
  });
});

describe('matchesMediaFilters', () => {
  const p = { resolution: '2160p', hdr_type: 'HDR10', audio_arc_ok: false };
  test('filters combine', () => {
    expect(matchesMediaFilters(p, { resolution: '2160p', hdr: 'any', audio: 'flagged' })).toBe(true);
    expect(matchesMediaFilters(p, { resolution: '1080p' })).toBe(false);
    expect(matchesMediaFilters(p, { hdr: 'none' })).toBe(false);
    expect(matchesMediaFilters(p, { audio: 'ok' })).toBe(false);
    expect(matchesMediaFilters({ audio_arc_ok: null }, { audio: 'flagged' })).toBe(false);
    expect(matchesMediaFilters(p, {})).toBe(true);
  });
});
