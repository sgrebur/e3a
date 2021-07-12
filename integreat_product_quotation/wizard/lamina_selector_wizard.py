# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class LaminaSelection(models.TransientModel):
    _inherit = 'wizard.lamina.selection'

    quotation_id = fields.Many2one('product.quotation.integreat')

    def action_add_to_quot(self):
        if self.quotation_id and self.quotation_id.bom_id:
            if self.quotation_id.bom_line_ids:
                lamina_bom_lines = self.quotation_id.bom_line_ids.filtered(
                    lambda x: x.product_id.categ_id == self.env.ref('integreat_sale_product_configurator.lamina'))
                lamina_bom_lines.sudo().unlink()
            line = self.line_ids.filtered(lambda x: x.select)
            if line[0].qty_per_component > 0 and self.pza_por_herr > 0:
                lamina_factor = line[0].qty_per_component
            else:
                lamina_factor = 1
            vals = {
                'bom_id': self.quotation_id.bom_id.id,
                'product_id': line[0].product_id.id,
                'product_qty': 1,
                'lamina_factor': lamina_factor
            }
            self.env['mrp.bom.line'].sudo().create(vals)
            self.unlink()
            return True
