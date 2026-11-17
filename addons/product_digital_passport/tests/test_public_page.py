from odoo import Command
from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestPublicPage(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        material = cls.env["dpp.material"].create({"name": "Test glass", "emission_factor": 1.0})
        cls.product = cls.env["product.template"].create(
            {
                "name": "Public Test Bottle",
                "dpp_enabled": True,
                "dpp_material_line_ids": [Command.create({"material_id": material.id, "weight_kg": 0.5})],
            }
        )

    def test_page_is_public(self):
        # No login: url_open runs as an anonymous visitor
        response = self.url_open("/passport/%s" % self.product.dpp_token)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Public Test Bottle", response.text)
        self.assertIn("Test glass", response.text)

    def test_json_endpoint(self):
        response = self.url_open("/passport/%s/json" % self.product.dpp_token)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Public Test Bottle")
        self.assertAlmostEqual(data["carbon_footprint_kg_co2e"]["total"], 0.5)
        self.assertEqual(len(data["materials"]), 1)

    def test_unknown_token_returns_404(self):
        response = self.url_open("/passport/not-a-real-token")
        self.assertEqual(response.status_code, 404)

    def test_disabled_passport_returns_404(self):
        token = self.product.dpp_token
        self.product.dpp_enabled = False
        self.env.flush_all()  # write the change to the database before the HTTP request
        response = self.url_open("/passport/%s" % token)
        self.assertEqual(response.status_code, 404)
