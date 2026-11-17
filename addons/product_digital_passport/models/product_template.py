import base64
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import is_html_empty

# Illustrative footprint rating by intensity (kg CO2e per kg of product).
# Upper bound of each band; anything above the last one is "E".
RATING_BANDS = [("a", 2.0), ("b", 5.0), ("c", 10.0), ("d", 20.0)]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    dpp_enabled = fields.Boolean(
        string="Digital Passport",
        help="Publish a public passport page for this product.",
    )
    dpp_token = fields.Char(string="Passport token", copy=False, readonly=True, index=True)
    dpp_url = fields.Char(string="Passport URL", compute="_compute_dpp_url")
    dpp_qr_code = fields.Binary(string="Passport QR", compute="_compute_dpp_qr_code")
    dpp_manufacturer_id = fields.Many2one("res.partner", string="Manufacturer")

    # Composition and carbon footprint
    dpp_material_line_ids = fields.One2many(
        "dpp.product.material", "product_tmpl_id", string="Material composition", copy=True
    )
    dpp_total_weight = fields.Float(
        string="Total weight (kg)", compute="_compute_dpp_footprint", store=True, digits=(16, 3)
    )
    dpp_co2_materials = fields.Float(
        string="Materials", compute="_compute_dpp_footprint", store=True, digits=(16, 2)
    )
    dpp_co2_manufacturing = fields.Float(string="Manufacturing", digits=(16, 2))
    dpp_co2_transport = fields.Float(string="Transport", digits=(16, 2))
    dpp_co2_total = fields.Float(
        string="Total CO2e (kg)", compute="_compute_dpp_footprint", store=True, digits=(16, 2)
    )
    dpp_footprint_rating = fields.Selection(
        [("a", "A"), ("b", "B"), ("c", "C"), ("d", "D"), ("e", "E")],
        string="Footprint rating",
        compute="_compute_dpp_footprint",
        store=True,
        help="Illustrative rating based on kg CO2e per kg of product.",
    )

    # Circularity
    dpp_recyclable_pct = fields.Float(
        string="Recyclable (% weight)", compute="_compute_dpp_footprint", store=True, digits=(16, 1)
    )
    dpp_recycled_pct = fields.Float(
        string="Recycled content (% weight)",
        compute="_compute_dpp_footprint",
        store=True,
        digits=(16, 1),
    )
    dpp_repairability_score = fields.Float(string="Repairability score (0-10)", digits=(16, 1))
    dpp_durability_years = fields.Integer(string="Expected lifetime (years)")
    dpp_spare_parts_years = fields.Integer(string="Spare parts available (years)")
    dpp_care_instructions = fields.Html(string="Use & care", translate=True)
    dpp_end_of_life = fields.Html(string="End of life & recycling", translate=True)

    _sql_constraints = [
        ("dpp_token_uniq", "unique(dpp_token)", "The passport token must be unique."),
    ]

    # ------------------------------------------------------------------
    # Computes
    # ------------------------------------------------------------------
    @api.depends(
        "dpp_material_line_ids.weight_kg",
        "dpp_material_line_ids.recycled_pct",
        "dpp_material_line_ids.co2_kg",
        "dpp_material_line_ids.material_id.recyclable",
        "dpp_co2_manufacturing",
        "dpp_co2_transport",
    )
    def _compute_dpp_footprint(self):
        for tmpl in self:
            lines = tmpl.dpp_material_line_ids
            weight = sum(lines.mapped("weight_kg"))
            co2_materials = sum(lines.mapped("co2_kg"))
            total = co2_materials + tmpl.dpp_co2_manufacturing + tmpl.dpp_co2_transport
            recyclable_weight = sum(line.weight_kg for line in lines if line.material_id.recyclable)
            recycled_weight = sum(line.weight_kg * line.recycled_pct / 100.0 for line in lines)

            tmpl.dpp_total_weight = weight
            tmpl.dpp_co2_materials = co2_materials
            tmpl.dpp_co2_total = total
            tmpl.dpp_recyclable_pct = recyclable_weight / weight * 100.0 if weight else 0.0
            tmpl.dpp_recycled_pct = recycled_weight / weight * 100.0 if weight else 0.0
            tmpl.dpp_footprint_rating = self._dpp_rating(total / weight) if weight else False

    @api.model
    def _dpp_rating(self, intensity):
        for rating, upper_bound in RATING_BANDS:
            if intensity < upper_bound:
                return rating
        return "e"

    @api.depends("dpp_token")
    def _compute_dpp_url(self):
        for tmpl in self:
            if tmpl.dpp_token:
                tmpl.dpp_url = "%s/passport/%s" % (tmpl.get_base_url(), tmpl.dpp_token)
            else:
                tmpl.dpp_url = False

    @api.depends("dpp_url")
    def _compute_dpp_qr_code(self):
        report = self.env["ir.actions.report"]
        for tmpl in self:
            if tmpl.dpp_url:
                png = report.barcode("QR", tmpl.dpp_url, width=300, height=300)
                tmpl.dpp_qr_code = base64.b64encode(png)
            else:
                tmpl.dpp_qr_code = False

    @api.constrains("dpp_repairability_score")
    def _check_dpp_repairability_score(self):
        for tmpl in self:
            if not 0 <= tmpl.dpp_repairability_score <= 10:
                raise ValidationError(_("The repairability score must be between 0 and 10."))

    # ------------------------------------------------------------------
    # Token handling: every product with a passport gets a random,
    # unguessable token that is used in its public URL.
    # ------------------------------------------------------------------
    @api.model
    def _dpp_new_token(self):
        return secrets.token_urlsafe(16)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("dpp_enabled") and not vals.get("dpp_token"):
                vals["dpp_token"] = self._dpp_new_token()
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if vals.get("dpp_enabled"):
            for tmpl in self.filtered(lambda t: not t.dpp_token):
                tmpl.dpp_token = self._dpp_new_token()
        return res

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_dpp_open_public_page(self):
        self.ensure_one()
        return {"type": "ir.actions.act_url", "url": self.dpp_url, "target": "new"}

    def action_dpp_regenerate_token(self):
        for tmpl in self:
            tmpl.dpp_token = self._dpp_new_token()

    # ------------------------------------------------------------------
    # Public data (used by the public page and the JSON endpoint)
    # ------------------------------------------------------------------
    def _dpp_public_data(self):
        self.ensure_one()
        total = self.dpp_co2_total

        def share(value):
            return round(value / total * 100.0, 1) if total else 0.0

        return {
            "name": self.name,
            "reference": self.default_code or "",
            "manufacturer": self.dpp_manufacturer_id.name or "",
            "rating": (self.dpp_footprint_rating or "").upper(),
            "carbon_footprint_kg_co2e": {
                "materials": round(self.dpp_co2_materials, 2),
                "manufacturing": round(self.dpp_co2_manufacturing, 2),
                "transport": round(self.dpp_co2_transport, 2),
                "total": round(total, 2),
                "share_pct": {
                    "materials": share(self.dpp_co2_materials),
                    "manufacturing": share(self.dpp_co2_manufacturing),
                    "transport": share(self.dpp_co2_transport),
                },
            },
            "weight_kg": round(self.dpp_total_weight, 3),
            "recyclable_pct": round(self.dpp_recyclable_pct, 1),
            "recycled_content_pct": round(self.dpp_recycled_pct, 1),
            "repairability_score": self.dpp_repairability_score,
            "expected_lifetime_years": self.dpp_durability_years,
            "spare_parts_years": self.dpp_spare_parts_years,
            "has_care_instructions": not is_html_empty(self.dpp_care_instructions),
            "has_end_of_life": not is_html_empty(self.dpp_end_of_life),
            "materials": [
                {
                    "component": line.component or "",
                    "material": line.material_id.name,
                    "weight_kg": round(line.weight_kg, 3),
                    "recycled_pct": round(line.recycled_pct, 1),
                    "origin": line.origin_country_id.name or "",
                    "recyclable": line.recyclable,
                    "hazardous": line.material_id.hazardous,
                    "co2_kg": round(line.co2_kg, 2),
                }
                for line in self.dpp_material_line_ids
            ],
            "last_update": fields.Datetime.to_string(self.write_date),
        }
