# -*- coding: utf-8 -*-

from odoo import api, models, fields


class StockMoveDoneWizard(models.TransientModel):
    _name = 'stock.move.done.wizard'
    _description = 'Stock Move Done Increase'

    picking_id = fields.Many2one('stock.picking')
    line_ids = fields.One2many('stock.move.done.line.wizard', 'wiz_id')
    increase_done = fields.Boolean('Aumentar las cantidades en un 10% cuando sea posible')
    show_button = fields.Boolean(compute='_show_button')

    @api.depends('line_ids.quantity_increased')
    def _show_button(self):
        for rec in self:
            if sum(rec.picking_id.move_line_ids.mapped('qty_done')) != sum(rec.line_ids.mapped('quantity_increased')):
                rec.show_button = True
            else:
                rec.show_button = False

    def _action_update_done_qty(self):
        for line in self.line_ids:
            if line.quantity_increased > line.quantity_done:
                free_quants = self.env['stock.quant'].search([
                    ('company_id', '=', line.move_id.company_id.id),
                    ('product_id', '=', line.product_id.id),
                    ('location_id', 'child of', line.move_id.location_id),
                ])



class StockMoveDoneLineWizard(models.TransientModel):
    _name = 'stock.move.done.line.wizard'
    _description = 'Stock Move Done Increase'

    wiz_id = fields.Many2one('stock.move.done.wizard')
    move_id = fields.Many2one('stock.move')
    product_id = fields.Many2one(related='move_id.product_id')
    free_qty = fields.Float('Ctd Libre', compute='_compute_free_qty')
    product_uom_qty = fields.Float(related='move_id.product_uom_qty')
    quantity_done = fields.Float(related='move_id.quantity_done')
    quantity_increased = fields.Float('Hecho', digits='Product Unit of Measure', default=0)
    increase_qty = fields.Float('Ctd aumento', digits='Product Unit of Measure', default=0)
    product_uom = fields.Many2one(related='move_id.product_uom')

    @api.depends('move_id.product_id')
    def _compute_free_qty(self):
        for rec in self:
            rec.qty_free = rec.move_id.product_id.with_context(location=rec.move_id.location_id).free_qty or 0
