import unittest

from cart import total_cents


class CartTest(unittest.TestCase):
    def test_no_discount(self):
        self.assertEqual(total_cents([(250, 2), (100, 1)]), 600)

    def test_round_half_up(self):
        # 1050 * 15% = 157.5 -> discount 158
        self.assertEqual(total_cents([(1050, 1)], 15), 892)

    def test_empty(self):
        self.assertEqual(total_cents([], 20), 0)


if __name__ == "__main__":
    unittest.main()
