# ?? 2018 ForgeFlow (https://www.forgeflow.com)
# @author Jordi Ballester <jordi.ballester@forgeflow.com.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.location"

    allow_negative_stock = fields.Boolean(
        string="Allow Negative Stock",
        help="Allow negative stock levels for the stockable products "
        "attached to this location.",
    )
    auto_adjust = fields.Boolean(string="Auto adjust negative stock to 0")

    def _get_parent_view(self):
        if self.location_id and self.location_id.usage == 'view':
            return self.location_id
        elif self.location_id:
            return self.location_id._get_parent_view()
        else:
            return self.env["res.partner"]
