"""Preroll media facts from ffprobe.

Pure helpers: they take ffprobe's JSON and return plain values, so they can be
tested without ffmpeg. main.py supplies the subprocess runner and the tool paths.

An ARC / Dolby Digital-only chain (projector -> ARC -> soundbar) only passes
Dolby Digital and Dolby Digital Plus. DTS, TrueHD, FLAC and PCM come out silent
or as stereo, and so does multichannel AAC / Opus.
"""
import json
import os
from typing import Optional

ARC_PASS_CODECS = {"ac3", "eac3"}
# Passes only as stereo/mono, where the source decodes to plain 2.0 PCM.
ARC_STEREO_CODECS = {"aac", "mp3", "mp2", "opus", "vorbis"}
ARC_FAIL_CODECS = {"truehd", "mlp", "flac"}  # plus dts*, dca and pcm* by prefix

ARC_WARNING = "This audio may not pass an ARC / Dolby Digital-only chain"


def classify_resolution(width, height) -> Optional[str]:
    """"2160p", "1080p" ... by the larger of what the frame size says.

    Scope and ultrawide films are letterboxed to a smaller height than their
    class (a 4K scope master is 3840x1600), so width counts too.
    """
    try:
        w, h = int(width or 0), int(height or 0)
    except (TypeError, ValueError):
        return None
    if w <= 0 and h <= 0:
        return None
    if h >= 1900 or w >= 3400:
        return "2160p"
    if h >= 1300 or w >= 2400:
        return "1440p"
    if h >= 1000 or w >= 1800:
        return "1080p"
    if h >= 700 or w >= 1200:
        return "720p"
    if h >= 560:
        return "576p"
    if h >= 460:
        return "480p"
    return f"{h}p" if h else None


def resolution_height(label) -> int:
    """2160 for "2160p", "4k", "uhd" and 2160; 0 when unknown."""
    text = str(label or "").strip().lower().replace(" ", "")
    if text in ("4k", "uhd", "2160", "2160p"):
        return 2160
    if text in ("8k", "4320", "4320p"):
        return 4320
    if text in ("sd",):
        return 480
    digits = text.rstrip("pi")
    return int(digits) if digits.isdigit() else 0


def classify_hdr(video: dict) -> str:
    """"Dolby Vision", "HDR10", "HLG" or "SDR" for one ffprobe video stream."""
    video = video or {}
    for side in video.get("side_data_list") or []:
        kind = str((side or {}).get("side_data_type", "")).lower()
        if "dovi" in kind or "dolby vision" in kind:
            return "Dolby Vision"
    if str(video.get("codec_tag_string", "")).lower() in ("dvh1", "dvhe", "dav1"):
        return "Dolby Vision"
    transfer = str(video.get("color_transfer", "")).lower()
    if transfer == "smpte2084":
        return "HDR10"
    if transfer == "arib-std-b67":
        return "HLG"
    return "SDR"


def normalize_audio_codec(codec) -> Optional[str]:
    name = str(codec or "").strip().lower()
    return name or None


def arc_ok(codec, channels) -> Optional[bool]:
    """True when the audio passes a Dolby Digital-only ARC chain, False when it
    won't, None when there is no audio or the codec isn't one we know."""
    name = normalize_audio_codec(codec)
    if not name:
        return None
    if name in ARC_PASS_CODECS:
        return True
    if name.startswith(("dts", "dca", "pcm")) or name in ARC_FAIL_CODECS:
        return False
    if name in ARC_STEREO_CODECS:
        return None if not channels else int(channels) <= 2
    return None


def parse_probe(data: dict) -> dict:
    """Preroll columns from `ffprobe -print_format json -show_streams` output."""
    streams = (data or {}).get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"
                  and not (s.get("disposition") or {}).get("attached_pic")), None)
    audios = [s for s in streams if s.get("codec_type") == "audio"]
    audio = next((s for s in audios if (s.get("disposition") or {}).get("default")), None) or (audios[0] if audios else None)
    codec = normalize_audio_codec((audio or {}).get("codec_name"))
    channels = (audio or {}).get("channels")
    return {
        "resolution": classify_resolution(video.get("width"), video.get("height")) if video else None,
        "video_codec": (video or {}).get("codec_name"),
        "hdr_type": classify_hdr(video) if video else None,
        "audio_codec": codec,
        "audio_channels": int(channels) if channels else None,
        "audio_arc_ok": arc_ok(codec, channels),
    }


def probe_media(path: str, ffprobe_cmd: str, run) -> Optional[dict]:
    """Probe one file. `run` is main._run_subprocess. None when ffprobe fails."""
    result = run([ffprobe_cmd, "-v", "error", "-print_format", "json", "-show_streams", path],
                 capture_output=True, text=True, timeout=60)
    if result.returncode != 0 or not result.stdout:
        return None
    return parse_probe(json.loads(result.stdout))
