"""Per-film rule matching (backend/rules_engine.py), no database needed."""
import unittest

from backend import rules_engine as re_


def rule(conditions, **kw):
    return {"id": kw.pop("id", 1), "name": "r", "enabled": True, "priority": 0, "match": "all",
            "conditions": conditions, "action": {"type": "category", "id": 1}, **kw}


FILM = {"title": "Dune: Part Two", "year": 2024, "genres": ["Science Fiction", "Adventure"],
        "content_rating": "PG-13", "video_resolution": "4k", "hdr": "Dolby Vision",
        "audio_codec": "truehd", "audio_profile": "Dolby TrueHD + Dolby Atmos"}


class MatchTests(unittest.TestCase):
    def test_each_condition(self):
        for cond in ({"min_resolution": "2160p"}, {"hdr": True}, {"atmos": True},
                     {"genres": ["adventure"]}, {"content_ratings": ["pg-13"]}, {"title_contains": "DUNE"}):
            self.assertTrue(re_.rule_matches(rule(cond), FILM), cond)

    def test_each_condition_can_fail(self):
        for cond in ({"min_resolution": "2160p"}, {"hdr": True}, {"atmos": True},
                     {"genres": ["Horror"]}, {"content_ratings": ["R"]}, {"title_contains": "alien"}):
            film = {"title": "Plain", "genres": ["Comedy"], "content_rating": "G", "video_resolution": "1080p",
                    "hdr": "SDR", "audio_codec": "ac3"}
            self.assertFalse(re_.rule_matches(rule(cond), film), cond)

    def test_all_versus_any(self):
        cond = {"min_resolution": "2160p", "genres": ["Horror"]}
        self.assertFalse(re_.rule_matches(rule(cond), FILM))
        self.assertTrue(re_.rule_matches(rule(cond, match="any"), FILM))

    def test_unknown_facts_are_not_met(self):
        sparse = {"title": "Unknown"}
        for cond in ({"min_resolution": "1080p"}, {"hdr": True}, {"atmos": True}, {"genres": ["Drama"]}):
            self.assertFalse(re_.rule_matches(rule(cond, match="any"), sparse), cond)

    def test_no_conditions_or_disabled_never_match(self):
        self.assertFalse(re_.rule_matches(rule({}), FILM))
        self.assertFalse(re_.rule_matches(rule({"bogus": 1}), FILM))
        self.assertFalse(re_.rule_matches(rule({"hdr": True}, enabled=False), FILM))

    def test_resolution_comparison(self):
        r = rule({"min_resolution": "1080p"})
        self.assertTrue(re_.rule_matches(r, {"video_resolution": "2160p"}))
        self.assertTrue(re_.rule_matches(r, {"video_resolution": "1080"}))
        self.assertFalse(re_.rule_matches(r, {"video_resolution": "720p"}))

    def test_hdr_values(self):
        self.assertFalse(re_.film_has_hdr({"hdr": "SDR"}))
        self.assertTrue(re_.film_has_hdr({"hdr": "HDR10"}))
        self.assertTrue(re_.film_has_hdr({"hdr": True}))
        self.assertIsNone(re_.film_has_hdr({}))

    def test_atmos_from_flag_or_text(self):
        self.assertTrue(re_.film_has_atmos({"atmos": True}))
        self.assertTrue(re_.film_has_atmos({"audio_codec": "eac3", "audio_profile": "Dolby Digital Plus + Dolby Atmos"}))
        self.assertFalse(re_.film_has_atmos({"audio_codec": "dts"}))
        self.assertIsNone(re_.film_has_atmos({}))


class ChooseTests(unittest.TestCase):
    def test_highest_priority_then_lowest_id(self):
        low = rule({"hdr": True}, id=1, priority=1)
        high = rule({"hdr": True}, id=2, priority=5)
        tie = rule({"hdr": True}, id=3, priority=5)
        self.assertEqual(re_.choose_rule([low, tie, high], FILM)["id"], 2)

    def test_skips_non_matching_and_returns_none(self):
        miss = rule({"genres": ["Horror"]}, id=1, priority=9)
        hit = rule({"hdr": True}, id=2)
        self.assertEqual(re_.choose_rule([miss, hit], FILM)["id"], 2)
        self.assertIsNone(re_.choose_rule([miss], FILM))
        self.assertIsNone(re_.choose_rule([], FILM))


class NormalizeTests(unittest.TestCase):
    def test_drops_unset_and_unknown(self):
        out = re_.normalize_conditions({"min_resolution": "", "hdr": False, "genres": [], "title_contains": " ",
                                        "content_ratings": "R, PG-13", "bogus": 1, "atmos": True})
        self.assertEqual(out, {"atmos": True, "content_ratings": ["r", "pg-13"]})

    def test_bad_resolution_is_dropped(self):
        self.assertEqual(re_.normalize_conditions({"min_resolution": "huge"}), {})
        self.assertEqual(re_.normalize_conditions(None), {})


class MediaItemTests(unittest.TestCase):
    def test_jellyfin_item(self):
        item = {"Name": "Dune", "ProductionYear": 2021, "Genres": ["Sci-Fi"], "OfficialRating": "PG-13",
                "MediaStreams": [
                    {"Type": "Video", "Width": 3840, "Height": 1600, "VideoRangeType": "DOVIWithHDR10"},
                    {"Type": "Audio", "Codec": "eac3", "Profile": "Dolby Digital Plus + Dolby Atmos", "IsDefault": True}]}
        film = re_.film_from_media_item(item)
        self.assertEqual(film["video_resolution"], "2160p")
        self.assertTrue(film["hdr"])
        self.assertTrue(re_.rule_matches(rule({"min_resolution": "2160p", "hdr": True, "atmos": True,
                                               "content_ratings": ["PG-13"]}), film))

    def test_sdr_and_missing_streams(self):
        film = re_.film_from_media_item({"Name": "x", "MediaStreams": [{"Type": "Video", "Width": 1920, "Height": 1080, "VideoRangeType": "SDR"}]})
        self.assertFalse(film["hdr"])
        self.assertEqual(film["video_resolution"], "1080p")
        self.assertIsNone(re_.film_from_media_item({"Name": "x"})["hdr"])


if __name__ == "__main__":
    unittest.main()
