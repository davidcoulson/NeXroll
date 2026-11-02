"""Pure helpers behind the preroll media badges and the DD+ conversion."""
import json
import unittest

from backend import media_probe as mp


def video(**kw):
    return {"codec_type": "video", "codec_name": "hevc", "width": 3840, "height": 2160, **kw}


def audio(codec="ac3", channels=6, **kw):
    return {"codec_type": "audio", "codec_name": codec, "channels": channels, **kw}


class ResolutionTests(unittest.TestCase):
    def test_classes(self):
        for size, label in [((3840, 2160), "2160p"), ((3840, 1600), "2160p"), ((1920, 1080), "1080p"),
                            ((1920, 800), "1080p"), ((1280, 720), "720p"), ((720, 480), "480p"),
                            ((720, 576), "576p"), ((320, 240), "240p")]:
            self.assertEqual(mp.classify_resolution(*size), label, size)

    def test_unknown(self):
        self.assertIsNone(mp.classify_resolution(None, None))
        self.assertIsNone(mp.classify_resolution(0, 0))
        self.assertIsNone(mp.classify_resolution("x", "y"))

    def test_height_labels(self):
        self.assertEqual(mp.resolution_height("4K"), 2160)
        self.assertEqual(mp.resolution_height("1080p"), 1080)
        self.assertEqual(mp.resolution_height(720), 720)
        self.assertEqual(mp.resolution_height("weird"), 0)


class HdrTests(unittest.TestCase):
    def test_sdr(self):
        self.assertEqual(mp.classify_hdr(video(color_transfer="bt709")), "SDR")
        self.assertEqual(mp.classify_hdr({}), "SDR")

    def test_hdr10_and_hlg(self):
        self.assertEqual(mp.classify_hdr(video(color_transfer="smpte2084", color_primaries="bt2020")), "HDR10")
        self.assertEqual(mp.classify_hdr(video(color_transfer="arib-std-b67")), "HLG")

    def test_dolby_vision_wins_over_transfer(self):
        side = [{"side_data_type": "DOVI configuration record"}]
        self.assertEqual(mp.classify_hdr(video(color_transfer="smpte2084", side_data_list=side)), "Dolby Vision")
        self.assertEqual(mp.classify_hdr(video(side_data_list=side)), "Dolby Vision")
        self.assertEqual(mp.classify_hdr(video(codec_tag_string="dvh1")), "Dolby Vision")


class ArcTests(unittest.TestCase):
    def test_dolby_digital_passes(self):
        self.assertTrue(mp.arc_ok("ac3", 6))
        self.assertTrue(mp.arc_ok("eac3", 8))

    def test_lossless_and_dts_fail(self):
        for codec in ("dts", "dts-hd ma", "truehd", "flac", "pcm_s16le", "pcm_s24le", "mlp"):
            self.assertFalse(mp.arc_ok(codec, 2), codec)

    def test_stereo_lossy_passes_multichannel_fails(self):
        for codec in ("aac", "mp3", "opus"):
            self.assertTrue(mp.arc_ok(codec, 2), codec)
            self.assertTrue(mp.arc_ok(codec, 1), codec)
            self.assertFalse(mp.arc_ok(codec, 6), codec)
        self.assertIsNone(mp.arc_ok("aac", None))

    def test_unknown(self):
        self.assertIsNone(mp.arc_ok(None, 2))
        self.assertIsNone(mp.arc_ok("", 2))
        self.assertIsNone(mp.arc_ok("alac", 2))


class ParseTests(unittest.TestCase):
    def test_full_stream_set(self):
        data = {"streams": [video(color_transfer="smpte2084"), audio("truehd", 8)]}
        self.assertEqual(mp.parse_probe(data), {
            "resolution": "2160p", "video_codec": "hevc", "hdr_type": "HDR10",
            "audio_codec": "truehd", "audio_channels": 8, "audio_arc_ok": False})

    def test_cover_art_is_not_the_video_and_default_audio_wins(self):
        art = {"codec_type": "video", "codec_name": "mjpeg", "width": 4000, "height": 4000, "disposition": {"attached_pic": 1}}
        data = {"streams": [art, video(width=1920, height=1080), audio("dts", 6), audio("ac3", 6, disposition={"default": 1})]}
        out = mp.parse_probe(data)
        self.assertEqual((out["resolution"], out["audio_codec"], out["audio_arc_ok"]), ("1080p", "ac3", True))

    def test_no_audio_or_video(self):
        out = mp.parse_probe({"streams": [video()]})
        self.assertIsNone(out["audio_codec"])
        self.assertIsNone(out["audio_arc_ok"])
        out = mp.parse_probe({})
        self.assertIsNone(out["resolution"])
        self.assertIsNone(out["hdr_type"])

    def test_probe_media_uses_the_runner(self):
        class Result:
            returncode, stdout = 0, json.dumps({"streams": [video(), audio("eac3", 6)]})
        calls = []
        def run(cmd, **kw):
            calls.append(cmd)
            return Result()
        out = mp.probe_media("/x/a.mp4", "ffprobe", run)
        self.assertTrue(out["audio_arc_ok"])
        self.assertEqual(calls[0][0], "ffprobe")
        self.assertEqual(calls[0][-1], "/x/a.mp4")

    def test_probe_media_failure_is_none(self):
        class Bad:
            returncode, stdout = 1, ""
        self.assertIsNone(mp.probe_media("/x/a.mp4", "ffprobe", lambda *a, **k: Bad()))


class ConvertCommandTests(unittest.TestCase):
    def test_surround_becomes_eac3_51(self):
        cmd = mp.build_eac3_cmd("ffmpeg", "/p/a.mkv", "/p/.a.converting.mkv", 8)
        self.assertEqual(cmd[0], "ffmpeg")
        self.assertEqual(cmd[cmd.index("-c:v") + 1], "copy")
        self.assertEqual(cmd[cmd.index("-c:a") + 1], "eac3")
        self.assertEqual(cmd[cmd.index("-b:a") + 1], "640k")
        self.assertEqual(cmd[cmd.index("-ac") + 1], "6")
        self.assertEqual(cmd[-1], "/p/.a.converting.mkv")
        self.assertNotIn("-movflags", cmd)

    def test_stereo_and_mono_stay_two_channel(self):
        for channels in (1, 2, None):
            cmd = mp.build_eac3_cmd("ffmpeg", "/p/a.mp4", "/p/.a.converting.mp4", channels)
            self.assertEqual(cmd[cmd.index("-ac") + 1], "2", channels)
        self.assertIn("+faststart", cmd)

    def test_input_is_a_single_argument_not_shell_text(self):
        cmd = mp.build_eac3_cmd("ffmpeg", "/p/a; rm -rf x.mkv", "/p/out.mkv", 6)
        self.assertEqual(cmd[cmd.index("-i") + 1], "/p/a; rm -rf x.mkv")

    def test_containers(self):
        self.assertTrue(mp.can_convert("/p/a.MKV"))
        self.assertFalse(mp.can_convert("/p/a.webm"))
        self.assertFalse(mp.can_convert("/p/a"))


if __name__ == "__main__":
    unittest.main()
