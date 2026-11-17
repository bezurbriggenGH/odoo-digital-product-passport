{
    "name": "Product Digital Passport",
    "summary": "EU Digital Product Passport (ESPR) with carbon footprint and a public QR page",
    "description": """
Digital Product Passport for Odoo
=================================
* Material composition per product (weight, recycled content, origin).
* Carbon footprint (kg CO2e): materials + manufacturing + transport.
* Circularity indicators: recyclable share, recycled content, repairability.
* Public passport page reachable through a QR code, plus a JSON endpoint.
* Printable QR label.
""",
    "version": "18.0.1.0.0",
    "category": "Sustainability",
    "license": "LGPL-3",
    "author": "Benjamin Zurbriggen",
    "website": "https://github.com/bezurbriggenGH/odoo-digital-product-passport",
    "depends": ["product"],
    "data": [
        "security/ir.model.access.csv",
        "data/dpp_material_data.xml",
        "views/dpp_material_views.xml",
        "views/product_template_views.xml",
        "views/passport_templates.xml",
        "report/passport_label_report.xml",
        "views/dpp_menus.xml",
    ],
    "demo": [
        "demo/product_demo.xml",
    ],
    "application": True,
    "installable": True,
}
