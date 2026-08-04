import unittest

from generar_precios_a_modificar import clean_card_name, price_recommendation


class PriceRecommendationTest(unittest.TestCase):
    def test_card_name_excludes_its_number(self) -> None:
        self.assertEqual(clean_card_name("Wally's Compassion 132/188"), "Wally's Compassion")

    def test_equal_to_market_minimum_is_maintained(self) -> None:
        recommendation = price_recommendation(current_price=0.50, market_minimum=0.50, stock=1)
        self.assertEqual((recommendation["decision"], recommendation["suggested_price"]), ("Mantener", 0.50))

    def test_lowering_matches_the_market_minimum_without_undercutting(self) -> None:
        recommendation = price_recommendation(current_price=0.50, market_minimum=0.40, stock=1)
        self.assertEqual((recommendation["decision"], recommendation["suggested_price"]), ("Bajar", 0.40))

    def test_price_below_market_minimum_is_increased_to_that_minimum(self) -> None:
        recommendation = price_recommendation(current_price=0.30, market_minimum=0.50, stock=1)
        self.assertEqual((recommendation["decision"], recommendation["suggested_price"]), ("Subir", 0.50))

    def test_only_high_stock_can_use_the_lower_floor(self) -> None:
        standard = price_recommendation(current_price=0.50, market_minimum=0.20, stock=10)
        high_stock = price_recommendation(current_price=0.50, market_minimum=0.20, stock=11)
        self.assertEqual((standard["floor"], high_stock["floor"]), (0.30, 0.15))

    def test_floor_that_matches_my_price_is_maintained(self) -> None:
        recommendation = price_recommendation(current_price=0.30, market_minimum=0.20, stock=10)
        self.assertEqual((recommendation["suggested_price"], recommendation["decision"]), (0.30, "Mantener"))


if __name__ == "__main__":
    unittest.main()
