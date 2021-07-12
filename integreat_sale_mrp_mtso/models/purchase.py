# -*- coding: utf-8 -*-
# greburs by InteGreat

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.tools import float_round


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    sale_order_ids = fields.Many2many(comodel_name="sale.order", string="OV",
        compute="_compute_from_group_id", store=True)
    production_ids = fields.Many2many(comodel_name="mrp.production", string="OP",
        compute="_compute_from_group_id", store=True)

    @api.depends('group_id.sale_order_ids', 'group_id.mrp_production_ids', 'group_id.production_ids')
    def _compute_from_group_id(self):
        for purchase in self:
            purchase.sale_order_ids = [(6, 0, purchase.group_id.sale_order_ids.ids +
                purchase.order_line.purchase_request_lines.mapped('sale_line_id.order_id.id'))]
            purchase.production_ids = [(6, 0, purchase.group_id.mrp_production_ids.ids +
                purchase.order_line.purchase_request_lines.mapped('request_id.group_id.mrp_production_ids').ids)]

    @api.depends('order_line.move_dest_ids.group_id.mrp_production_ids', 'production_ids')
    def _compute_mrp_production_count(self):
        super(PurchaseOrder, self)._compute_mrp_production_count()
        for purchase in self:
            purchase._compute_from_group_id()
            purchase.mrp_production_count += len(purchase.production_ids)

    # OVERRIDE
    def _get_sale_orders(self):
        so = self.order_line.sale_order_id
        so += self.order_line.purchase_request_lines.sale_line_id.order_id
        return so

    # OVERRIDE
    def action_view_mrp_productions(self):
        self.ensure_one()
        mrp_production_ids = (
                self.order_line.move_dest_ids.group_id.mrp_production_ids |
                self.order_line.move_ids.move_dest_ids.group_id.mrp_production_ids |
                self.production_ids
        ).ids
        action = {
            'res_model': 'mrp.production',
            'type': 'ir.actions.act_window',
        }
        if len(mrp_production_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': mrp_production_ids[0],
            })
        else:
            action.update({
                'name': _("Manufacturing Source of %s", self.name),
                'domain': [('id', 'in', mrp_production_ids)],
                'view_mode': 'tree,form',
            })
        return action

    def _add_supplier_to_product(self):
        # OVERRIDE: we do not want prices to be added to supplierinfo!
        return


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    manual_price = fields.Boolean(compute='_compute_is_manual_price')

    @api.onchange('price_unit')
    def _compute_is_manual_price(self):
        for line in self:
            line.manual_price = False
            if line.product_id and line.price_unit != 0.0:
                params = {'order_id': line.order_id}
                seller = line.product_id._select_seller(
                    partner_id=line.partner_id,
                    quantity=line.product_qty,
                    date=line.order_id.date_order and line.order_id.date_order.date(),
                    uom_id=line.product_uom,
                    params=params)
                price_unit = self.env['account.tax']._fix_tax_included_price_company(seller.price,
                    line.product_id.supplier_taxes_id, line.taxes_id, line.company_id) if seller else 0.0
                if price_unit and seller and line.order_id.currency_id and seller.currency_id != line.order_id.currency_id:
                    price_unit = seller.currency_id._convert(price_unit, self.order_id.currency_id,
                        line.order_id.company_id, line.date_order or fields.Date.today())
                if seller and line.product_uom and seller.product_uom != self.product_uom:
                    price_unit = seller.product_uom._compute_price(price_unit, line.product_uom)
                if price_unit != round(line.price_unit, ndigits=6):
                    line.manual_price = True
            else:
                line.manual_price = True
