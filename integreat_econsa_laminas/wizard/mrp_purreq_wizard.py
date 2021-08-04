# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools import float_round
from odoo.exceptions import ValidationError


class MrpPurchaseRequest(models.TransientModel):
    _name = 'mrp.purchase.request.wizard'
    _description = 'MRP Purchase Request Wizard'

    production_id = fields.Many2one('mrp.production')
    line_ids = fields.One2many('mrp.purchase.request.wizard.line', 'wiz_id')
    selected = fields.Boolean(compute='_compute_selected')

    @api.depends('line_ids.selected')
    def _compute_selected(self):
        for wiz in self:
            if any(wiz.line_ids.mapped('selected')):
                wiz.selected = True
            else:
                wiz.selected = False

    def button_create_purreq(self):
        for wiz in self:
            for line in wiz.line_ids:
                wiz.production_id._run_lamina_procurement(line.product_id, line.req_qty, [line])
        self.unlink()


class MrpPurchaseRequestLine(models.TransientModel):
    _name = 'mrp.purchase.request.wizard.line'
    _description = 'MRP Purchase Request Wizard Line'

    wiz_id = fields.Many2one('mrp.purchase.request.wizard', ondelete='set null')
    move_id = fields.Many2one('stock.move')
    product_id = fields.Many2one(related='move_id.product_id')
    product_uom_qty = fields.Float(related='move_id.product_uom_qty')
    product_uom = fields.Many2one(related='move_id.product_uom')
    reserved_availability = fields.Float(related='move_id.reserved_availability')
    free_qty = fields.Float(related='product_id.free_qty')
    req_qty = fields.Float('Ctd solicitada', digits='Product Unit of Measure', compute='_compute_qty', store=True, readonly=False)
    selected = fields.Boolean('Sel.', default=True)

    @api.depends('move_id.reserved_availability', 'move_id.product_id.free_qty')
    def _compute_qty(self):
        for wiz in self:
            req_qty = wiz.product_uom_qty - wiz.reserved_availability - wiz.free_qty
            if req_qty > 0.0:
                wiz.req_qty = req_qty
            else:
                wiz.req_qty = 0.0
