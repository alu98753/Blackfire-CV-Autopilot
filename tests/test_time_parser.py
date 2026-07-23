import unittest
from utils.time_parser import parse_time_to_seconds, format_seconds_to_readable

class TestTimeParser(unittest.TestCase):
    def test_parse_hh_mm_ss(self):
        self.assertEqual(parse_time_to_seconds("01:30:44"), 5444)
        self.assertEqual(parse_time_to_seconds("00:18:43"), 1123)

    def test_parse_mm_ss(self):
        self.assertEqual(parse_time_to_seconds("16:35"), 995)
        self.assertEqual(parse_time_to_seconds("05:05"), 305)

    def test_parse_missing_colon_4_digits(self):
        # "0130" 應拆為 01 分 30 秒 (90s)
        self.assertEqual(parse_time_to_seconds("0130"), 90)
        # "0130:44" 冒號漏讀第一個，應拆為 ["01", "30", "44"] -> 1小時30分44秒 (5444s)
        self.assertEqual(parse_time_to_seconds("0130:44"), 5444)

    def test_parse_missing_colon_6_digits(self):
        # "013044" 全無冒號，應拆為 01:30:44 -> 5444s
        self.assertEqual(parse_time_to_seconds("013044"), 5444)

    def test_parse_invalid(self):
        self.assertIsNone(parse_time_to_seconds(""))
        self.assertIsNone(parse_time_to_seconds("abc"))

    def test_format_seconds_to_readable(self):
        self.assertEqual(format_seconds_to_readable(5444), "1 小時 30 分 44 秒")
        self.assertEqual(format_seconds_to_readable(995), "16 分 35 秒")
        self.assertEqual(format_seconds_to_readable(45), "45 秒")
        self.assertEqual(format_seconds_to_readable(0), "0 秒")
        self.assertEqual(format_seconds_to_readable(None), "0 秒")

if __name__ == "__main__":
    unittest.main()
