from odoo import fields, models


class DppMaterial(models.Model):
    """A material with its emission factors (kg CO2e per kg of material)."""

    _name = "dpp.material"
    _description = "Passport Material"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    code = fields.Char()
    active = fields.Boolean(default=True)
    category = fields.Selection(
        [
            ("metal", "Metal"),
            ("plastic", "Plastic"),
            ("textile", "Textile"),
            ("glass", "Glass"),
            ("paper", "Paper & cardboard"),
            ("wood", "Wood"),
            ("rubber", "Rubber"),
            ("electronic", "Electronics & batteries"),
            ("other", "Other"),
        ],
        required=True,
        default="other",
    )
    emission_factor = fields.Float(
        string="Emission factor (kg CO2e/kg)",
        digits=(16, 3),
        help="Emissions to produce 1 kg of virgin material.",
    )
    recycled_emission_factor = fields.Float(
        string="Recycled factor (kg CO2e/kg)",
        digits=(16, 3),
        help="Emissions to produce 1 kg of recycled material.",
    )
    recyclable = fields.Boolean(default=True)
    hazardous = fields.Boolean(help="Substance of concern that must be declared in the passport.")
    source = fields.Char(string="Factor source", help="Where the factor comes from, e.g. ecoinvent, DEFRA.")

    _sql_constraints = [
        ("code_uniq", "unique(code)", "The material code must be unique."),
        (
            "factors_positive",
            "CHECK(emission_factor >= 0 AND recycled_emission_factor >= 0)",
            "Emission factors cannot be negative.",
        ),
    ]
