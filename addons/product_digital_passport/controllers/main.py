from odoo import http
from odoo.http import request


class PassportController(http.Controller):
    """Public pages: no login needed, anyone scanning the QR can open them."""

    def _find_passport(self, token):
        # sudo() because visitors are not logged in. Only the fields listed
        # in _dpp_public_data() are shown to them.
        product = request.env["product.template"].sudo().search(
            [("dpp_token", "=", token), ("dpp_enabled", "=", True)], limit=1
        )
        if not product:
            raise request.not_found()
        return product

    @http.route("/passport/<string:token>", type="http", auth="public", methods=["GET"])
    def passport_page(self, token, **kwargs):
        product = self._find_passport(token)
        return request.render(
            "product_digital_passport.passport_public_page",
            {"product": product, "data": product._dpp_public_data()},
        )

    @http.route("/passport/<string:token>/json", type="http", auth="public", methods=["GET"])
    def passport_json(self, token, **kwargs):
        product = self._find_passport(token)
        return request.make_json_response(product._dpp_public_data())
