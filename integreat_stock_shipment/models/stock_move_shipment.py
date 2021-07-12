# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero
from collections import defaultdict


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    count_shipment = fields.Integer(compute='_compute_picking_count')
    count_picking_to_ship = fields.Integer(compute='_compute_picking_count')

    def _compute_picking_count(self):
        super(StockPickingType, self)._compute_picking_count()
        for record in self:
            if record.code == 'outgoing':
                record.count_picking_ready = len(self.env['stock.picking'].search([
                    ('picking_type_id', '=', record.id),
                    ('state', '=', 'assigned'),
                    ('shipment_state', 'in', ('not_relevant', 'ready', 'partial_available'))
                ]))
                record.count_picking_to_ship = len(self.env['stock.picking'].search([
                    ('picking_type_id', '=', record.id),
                    ('state', '=', 'assigned'),
                    ('shipment_state', '=', 'assign')
                ]))
                record.count_shipment = len(self.env['shipment'].search([
                    ('warehouse_id', '=', record.warehouse_id.id),
                    ('state', '=', 'loading'),
                ]))
            else:
                record.count_shipment = 0
                record.count_picking_to_ship = 0


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    incoterm = fields.Many2one(related='group_id.sale_id.incoterm', store=True)
    no_shipment = fields.Boolean('Entrega directa')
    shipment_id = fields.Many2one('shipment', 'Transporte', copy=False, index=True)
    assign_to_shipment = fields.Boolean('To be assigned to shipment')
    shipment_state = fields.Selection([
        ('not_relevant', 'Not relevante'),
        ('ready', 'Listo para Transporte'),
        ('assign', 'No asignado'),
        ('partial_available', 'Disponible parcialmente'),
        ('loading', 'En preparación'),
        ('shipped', 'Enviado')
    ], string='Estado envío', compute='_compute_shipment_state', copy=False, index=True, readonly=True, store=True)

    @api.depends('state', 'shipment_id', 'no_shipment', 'move_line_ids.product_qty', 'assign_to_shipment')
    def _compute_shipment_state(self):
        for p in self:
            if p.picking_type_code != 'outgoing' or p.state in ('draft', 'waiting', 'confirmed') or p.no_shipment:
                p.shipment_state = 'not_relevant'
            elif p.shipment_id:
                if sum(p.move_line_ids.mapped('product_uom_qty')) < sum(p.move_lines.mapped('product_uom_qty')):
                    p.shipment_state = 'partial_available'
                else:
                    p.shipment_state = p.shipment_id.state
            elif p.assign_to_shipment:
                p.shipment_state = 'assign'
            else:
                p.shipment_state = 'ready'

    def create_shipment(self):
        deliveries = self.filtered(lambda d: d.assign_to_shipment is True)\
                        .sorted(key=lambda d: (d.picking_type_id.warehouse_id.id, d.partner_id.id, d.scheduled_date))
        shipment = self.env['shipment']
        shipments = self.env['shipment']
        for p in deliveries:
            if shipment.partner_id != p.partner_id \
                    or shipment.warehouse_id != p.picking_type_id.warehouse_id \
                    or shipment.incoterm != p.incoterm:
                shipment = self.env['shipment'].create({
                    'warehouse_id': p.picking_type_id.warehouse_id.id,
                    'partner_id': p.partner_id.id,
                    'incoterm': p.incoterm.id,
                    'shipment_date': p.scheduled_date,
                })
                shipments |= shipment
            p.shipment_id = shipment
            p.assign_to_shipment = False
        if shipments:
            action = {
                'res_model': 'shipment',
                'type': 'ir.actions.act_window',
            }
            if len(shipments) == 1:
                action.update({
                    'view_mode': 'form',
                    'res_id': shipments[0].id,
                })
            else:
                action.update({
                    'name': "Transportes creadas",
                    'domain': [('id', 'in', shipments.ids)],
                    'view_mode': 'tree,form',
                })
            return action

    def button_validate(self):
        for p in self:
            if p.picking_type_code == 'outgoing' and not p.shipment_id and not p.no_shipment:
                raise UserError('Antes de validar debe asignar la entrega a un transporte\n'
                                'o marcar como no relevante para el transporte.')
            return super(StockPicking, self).button_validate()

    def button_ready_for_shipment(self):
        for p in self:
            p.action_assign()
            if p.state in ('draft', 'ready'):
                continue
            for ml in p.move_line_ids:
                if ml.qty_done == 0:
                    ml.qty_done = ml.product_uom_qty
            # rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            # if float_compare(sum(p.move_lines.mapped('quantity_done')), sum(p.move_lines.mapped('product_uom_qty')),
            #                      precision_digits=rounding) != 0:
            #     backorder_picking = p.copy({
            #         'name': '/',
            #         'move_lines': [],
            #         'move_line_ids': [],
            #         'backorder_id': p.id
            #     })
            #     p.message_post(body=_(
            #         'The backorder <a href=# data-oe-model=stock.picking data-oe-id=%d>%s</a> has been created.'
            #         ) % (backorder_picking.id, backorder_picking.name))
            #     moves = p.move_lines.exists().filtered(lambda x: x.state not in ('done', 'cancel'))
            #     # moves_todo = self.env['stock.move']
            #     # Split moves where necessary and move quants
            #     backorder_moves_vals = []
            #     for move in moves:
            #         # To know whether we need to create a backorder or not, round to the general product's
            #         # decimal precision and not the product's UOM.
            #         if float_compare(move.quantity_done, move.product_uom_qty, precision_digits=rounding) < 0:
            #             if move.quantity_done == 0:
            #                 move.write({'picking_id': backorder_picking.id})
            #             else:
            #                 # Need to do some kind of conversion here
            #                 qty_split = move.product_uom._compute_quantity(move.product_uom_qty - move.quantity_done,
            #                                                                move.product_id.uom_id,
            #                                                                rounding_method='HALF-UP')
            #                 new_move_vals = move._split(qty_split)
            #                 backorder_moves_vals += new_move_vals
            #     backorder_moves = self.env['stock.move'].create(backorder_moves_vals)
            #     backorder_moves.write({'picking_id': backorder_picking.id})
            #     backorder_moves._action_confirm(merge=False)
            #     backorder_picking.action_confirm()
            #     backorder_picking.action_assign()
            p.assign_to_shipment = True


class StockMove(models.Model):
    _inherit = 'stock.move'

    qty_loaded = fields.Float('Loaded', compute='_compute_shipped_qty', store=True, copy=False, digits='Product Unit of Measure')
    qty_to_load = fields.Float('To Load', compute='_compute_shipped_qty', store=True, copy=False, digits='Product Unit of Measure')
    move_shipping_line_ids = fields.One2many('stock.move.shipment', 'move_id', string='Shipping Lines')

    @api.depends('picking_id.shipment_id', 'move_shipping_line_ids.qty', 'move_line_ids.qty_done')
    def _compute_shipped_qty(self):
        for move in self:
            # move._quantity_done_compute()
            if move.picking_id.shipment_id:
                move.qty_loaded = sum(move.move_shipping_line_ids.mapped('qty'))
                move.qty_to_load = sum(move.move_line_ids.mapped('qty_done')) - move.qty_loaded
            else:
                move.qty_loaded = 0
                move.qty_to_load = 0


class StockMoveShipment(models.Model):
    _name = 'stock.move.shipment'
    _description = 'Stock Move Shipped'

    move_id = fields.Many2one('stock.move')
    shipment_id = fields.Many2one('shipment')
    shipment_line_id = fields.Many2one('shipment.line')
    sequence = fields.Integer(related='shipment_line_id.sequence')
    pack_type = fields.Many2one('shipment.package.type', compute='_compute_pack', inverse='_inverse_pack_type')
    pack_qty = fields.Integer(compute='_compute_pack', inverse='_inverse_pack_qty')
    qty = fields.Float('Qty', digits='Product Unit of Measure')
    product_id = fields.Many2one(related='move_id.product_id')
    product_uom = fields.Many2one(related='move_id.product_uom')
    sale_id = fields.Many2one(related='move_id.sale_line_id.order_id')
    client_order_ref = fields.Char(string='OC', related='sale_id.client_order_ref')

    @api.depends('shipment_line_id.pack_type', 'shipment_line_id.pack_qty')
    def _compute_pack(self):
        for rec in self:
            rec.pack_type = rec.shipment_line_id.pack_type
            rec.pack_qty = rec.shipment_line_id.pack_qty

    def _inverse_pack_type(self):
        for rec in self:
            rec.shipment_line_id.pack_type = rec.pack_type if rec.pack_type else False

    def _inverse_pack_qty(self):
        for rec in self:
            rec.shipment_line_id.pack_qty = rec.pack_qty if rec.pack_qty else False
