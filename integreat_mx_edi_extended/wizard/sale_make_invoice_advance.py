# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import time

from odoo import api, fields, models, _


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    advance_payment_method = fields.Selection(selection_add=[('force_ordered', 'Prefacturación')],
        ondelete={'force_ordered': 'set default'})

    def create_invoices(self):
        if self.advance_payment_method == 'force_ordered':
            sale_orders = self.env['sale.order'].browse(self._context.get('active_ids', []))
            sale_orders._force_lines_to_invoice_policy_order()
            self.advance_payment_method = 'delivered'
        return super(SaleAdvancePaymentInv, self).create_invoices()