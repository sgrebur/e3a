# coding: utf-8

from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    order_checked = fields.Boolean('Imprimado/Controlado')

    # OVERRIDE Print - Send logic
    def print_quotation(self):
        self.write({'order_checked': True})
        return self.env.ref('purchase.action_report_purchase_order').report_action(self)

    # OVERRIDE Print - Send logic
    def action_rfq_send(self):
        for order in self:
            if order.state == 'draft':
                order.write({'state': "sent"})
        return super().action_rfq_send()


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def get_seller_id_for_printout(self):
        seller = False
        if self.product_id:
            params = {'order_id': self.order_id}
            seller = self.product_id._select_seller(
                partner_id=self.partner_id,
                quantity=self.product_qty,
                date=self.order_id.date_order and self.order_id.date_order.date(),
                uom_id=self.product_uom,
                params=params)
        return seller