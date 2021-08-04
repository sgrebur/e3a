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
