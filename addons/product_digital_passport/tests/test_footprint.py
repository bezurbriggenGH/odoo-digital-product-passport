from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFootprint(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.steel = cls.env["dpp.material"].create(
            {
                "name": "Test steel",
                "emission_factor": 2.0,
                "recycled_emission_factor": 0.5,
                "recyclable": True,
            }
        )
        cls.plastic = cls.env["dpp.material"].create(
            {
                "name": "Test plastic",
                "emission_factor": 3.0,
                "recycled_emission_factor": 1.0,
                "recyclable": False,
            }
        )
        cls.product = cls.env["product.template"].create(
            {
                "name": "Test product",
                "dpp_enabled": True,
                "dpp_co2_manufacturing": 1.0,
                "dpp_co2_transport": 0.5,
                "dpp_material_line_ids": [
                    Command.create({"material_id": cls.steel.id, "weight_kg": 2.0, "recycled_pct": 50}),
                    Command.create({"material_id": cls.plastic.id, "weight_kg": 1.0}),
                ],
            }
        )

    def test_line_co2_mixes_virgin_and_recycled_factors(self):
        steel_line = self.product.dpp_material_line_ids.filtered(lambda l: l.material_id == self.steel)
        # 2 kg * (50% * 2.0 + 50% * 0.5) = 2.5
        self.assertAlmostEqual(steel_line.co2_kg, 2.5)

    def test_product_totals(self):
        product = self.product
        self.assertAlmostEqual(product.dpp_total_weight, 3.0)
        self.assertAlmostEqual(product.dpp_co2_materials, 5.5)  # 2.5 + 3.0
        self.assertAlmostEqual(product.dpp_co2_total, 7.0)  # 5.5 + 1.0 + 0.5
        # Percentages are stored with 1 decimal
        self.assertAlmostEqual(product.dpp_recyclable_pct, 66.7, places=1)  # 2 of 3 kg
        self.assertAlmostEqual(product.dpp_recycled_pct, 33.3, places=1)  # 1 of 3 kg
        # 7.0 kg CO2e / 3 kg = 2.33 -> band B
        self.assertEqual(product.dpp_footprint_rating, "b")

    def test_totals_follow_changes(self):
        self.product.dpp_co2_transport = 10.0
        self.assertAlmostEqual(self.product.dpp_co2_total, 16.5)
        self.steel.emission_factor = 4.0
        # steel line: 2 * (0.5 * 4.0 + 0.5 * 0.5) = 4.5
        self.assertAlmostEqual(self.product.dpp_co2_materials, 7.5)

    def test_rating_bands(self):
        rating = self.env["product.template"]._dpp_rating
        self.assertEqual(rating(1.9), "a")
        self.assertEqual(rating(2.0), "b")
        self.assertEqual(rating(9.99), "c")
        self.assertEqual(rating(19.0), "d")
        self.assertEqual(rating(50.0), "e")

    def test_product_without_materials_has_no_rating(self):
        product = self.env["product.template"].create({"name": "Empty", "dpp_enabled": True})
        self.assertFalse(product.dpp_footprint_rating)
        self.assertEqual(product.dpp_co2_total, 0.0)

    def test_token_created_and_unique(self):
        self.assertTrue(self.product.dpp_token)
        self.assertIn(self.product.dpp_token, self.product.dpp_url)
        copy = self.product.copy()
        self.assertTrue(copy.dpp_token)
        self.assertNotEqual(copy.dpp_token, self.product.dpp_token)

    def test_token_created_when_enabled_later(self):
        product = self.env["product.template"].create({"name": "Later"})
        self.assertFalse(product.dpp_token)
        product.dpp_enabled = True
        self.assertTrue(product.dpp_token)

    def test_regenerate_token(self):
        old = self.product.dpp_token
        self.product.action_dpp_regenerate_token()
        self.assertNotEqual(self.product.dpp_token, old)

    def test_qr_code_generated(self):
        self.assertTrue(self.product.dpp_qr_code)

    def test_label_report_renders(self):
        html, _format = self.env["ir.actions.report"]._render_qweb_html(
            "product_digital_passport.report_passport_label", self.product.ids
        )
        self.assertIn(b"Test product", html)
        self.assertIn(b"67%", html)  # recyclable share, rounded

    def test_invalid_values(self):
        with self.assertRaises(ValidationError):
            self.product.dpp_material_line_ids[0].recycled_pct = 120
        with self.assertRaises(ValidationError):
            self.product.dpp_repairability_score = 11
