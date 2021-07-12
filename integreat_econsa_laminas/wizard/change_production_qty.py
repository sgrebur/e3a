# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ChangeProductionQty(models.TransientModel):
    _inherit = 'change.production.qty'

    lamina_selector = fields.Many2one('wizard.lamina.selection')

    def change_prod_qty(self):
        if self.lamina_selector:
            super().change_prod_qty()
            self.lamina_selector.write({'qty': self.mo_id.product_qty})
            view_id = self.env.ref('integreat_econsa_laminas.wizard_lamina_selection_form').id
            return {
                        'name': 'Selección láminas',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'wizard.lamina.selection',
                        'view_id': view_id,
                        'target': 'new',
                        'res_id': self.lamina_selector.id,
                        'context': self.env.context
                    }
