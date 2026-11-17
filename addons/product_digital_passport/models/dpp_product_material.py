from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class DppProductMaterial(models.Model):
    """One line of a product's material composition."""

    _name = "dpp.product.material"
    _description = "Product Material Composition Line"
    _order = "sequence, id"

    sequence = fields.Integer(default=10)
    product_tmpl_id = fields.Many2one(
        "product.template", string="Product", required=True, ondelete="cascade", index=True
    )
    component = fields.Char(help="Part of the product, e.g. 'Frame' or 'Battery'.")
    material_id = fields.Many2one("dpp.material", string="Material", required=True, ondelete="restrict")
    weight_kg = fields.Float(string="Weight (kg)", digits=(16, 3))
    recycled_pct = fields.Float(string="Recycled content (%)", digits=(16, 1))
    origin_country_id = fields.Many2one("res.country", string="Origin")
    recyclable = fields.Boolean(related="material_id.recyclable")
    co2_kg = fields.Float(
        string="CO2e (kg)", compute="_compute_co2_kg", store=True, digits=(16, 3)
    )

    @api.depends(
        "weight_kg",
        "recycled_pct",
        "material_id.emission_factor",
        "material_id.recycled_emission_factor",
    )
    def _compute_co2_kg(self):
        for line in self:
            recycled_share = line.recycled_pct / 100.0
            factor = (
                (1 - recycled_share) * line.material_id.emission_factor
                + recycled_share * line.material_id.recycled_emission_factor
            )
            line.co2_kg = line.weight_kg * factor

    @api.constrains("weight_kg", "recycled_pct")
    def _check_values(self):
        for line in self:
            if line.weight_kg < 0:
                raise ValidationError(_("The weight cannot be negative."))
            if not 0 <= line.recycled_pct <= 100:
                raise ValidationError(_("Recycled content must be between 0 and 100%."))
