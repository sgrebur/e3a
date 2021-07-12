# -*- coding: utf-8 -*-
# greburs by InteGreat

from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    report_color = fields.Integer(compute='_compute_report_color')

    @api.depends('state')
    def _compute_report_color(self):
        for p in self:
            if p.state == 'assigned':
                p.report_color = 1
            elif p.state == 'done':
                p.report_color = 10
            else:
                p.report_color = 0


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    report_color = fields.Integer(compute='_compute_report_color')

    @api.depends('state')
    def _compute_report_color(self):
        for p in self:
            if p.state not in ('purchased', 'done'):
                p.report_color = 1
            else:
                p.report_color = 0
