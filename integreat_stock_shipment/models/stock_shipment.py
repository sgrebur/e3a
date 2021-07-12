# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class Shipment(models.Model):
    _name = 'shipment'
    _description = 'Shipment'
    _order = 'name desc'

    name = fields.Char('Shipment No.', default='Nuevo')
    shipment_date = fields.Date('Shipment Date')
    warehouse_id = fields.Many2one('stock.warehouse', required=True)
    partner_id = fields.Many2one('res.partner', string='Customer/Supplier', required=True)
    incoterm = fields.Many2one('account.incoterms', 'Incoterm',
        help='FCA = el cliente es responsable de recoger la mercancía, \n'
            'DAP = el vendedor es responsable de entregar la mercancía en la dirección de entrega')
    driver = fields.Char('Driver')
    plate_no = fields.Char('Plate No')
    picking_ids = fields.One2many('stock.picking', 'shipment_id', string='Deliveries')
    move_ids = fields.One2many('stock.move', compute='_compute_move_ids')
    move_line_ids = fields.One2many('stock.move.line', compute='_compute_move_ids')
    line_ids = fields.One2many('shipment.line', 'shipment_id', string='Lines')
    move_shipment_ids = fields.One2many('stock.move.shipment', 'shipment_id')
    state = fields.Selection([
        ('loading', 'En preparación'),
        ('shipped', 'Enviado'),
        ('cancel', 'Cancelado')
    ], string='Estado envío', default='loading', copy=False, index=True, readonly=True, store=True)
    single_order = fields.Char('Purchase Order', compute='_compute_order', store=True)
    #confirm_warning = fields.Integer(compute='_compute_confirm_warning')

    def action_assign(self):
        return self.picking_ids.action_assign()

    # @api.depends('move_ids.qty_to_load', 'move_line_ids')
    # def _compute_confirm_warning(self):
    #     for ship in self:
    #         ship.confirm_warning = 0
    #         for move in self.move_ids:
    #             if move.qty_to_load > 0 and move.quantity_done != move.qty_loaded:
    #                 ship.confirm_warning = 1
    #                 break

    def button_confirm(self):
        for shipment in self:
            shipment.state = 'shipped'
            return shipment.picking_ids.button_validate()

    def button_cancel(self):
        for shipment in self:
            shipment.move_shipment_ids.unlink()
            shipment.picking_ids = [(5, 0)]
            shipment.state = 'cancel'

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('shipment') or 'Nuevo'
        return super(Shipment, self).create(vals)

    @api.depends('picking_ids.move_line_ids.qty_done')
    def _compute_move_ids(self):
        for shpmnt in self:
            shpmnt.move_ids = shpmnt.picking_ids.move_lines.filtered(lambda m: m.qty_to_load > 0)
            shpmnt.move_line_ids = shpmnt.picking_ids.move_line_ids

    def button_move_load_wizard(self):
        lines = []
        for move in self.move_ids:
            lines.append([0, 0, {'move_id': move.id, 'loaded_qty': move.qty_to_load}])
        vals = {
            'shipment_id': self.id,
            'line_ids': lines
        }
        wiz = self.env['shipment.move.load.wizard'].create(vals)
        return wiz.wizard_action(wiz.id)

    @api.depends('move_shipment_ids.sale_id')
    def _compute_order(self):
        for shpmnt in self:
            orders = list(dict.fromkeys(shpmnt.move_shipment_ids.mapped('sale_id.client_order_ref')))
            if len(orders) == 1:
                shpmnt.single_order = orders[0]
            else:
                shpmnt.single_order = False

    @api.onchange('picking_ids', 'partner_id', 'warehouse_id')
    def _check_piking_warehouse(self):
        for shpmnt in self:
            warehouse = partner = []
            if shpmnt.warehouse_id:
                warehouse |= shpmnt.warehouse_id.id
            elif shpmnt.picking_ids:
                warehouse |= shpmnt.picking_ids[0].picking_type_id.warehouse_id.id
            if shpmnt.partner_id:
                partner |= shpmnt.partner_id.id
            elif shpmnt.picking_ids:
                partner |= shpmnt.picking_ids[0].partner_id.id
            return {
                'domain': {
                    'picking_ids': [('picking_type_id.code', '=', 'outgoing'),
                                    ('picking_type_id.warehouse_id', 'in', warehouse),
                                    ('partner_id', 'in', partner),
                                    ('shipment_state', '=', 'assign')]
                    }
            }


class ShipmentLine(models.Model):
    _name = 'shipment.line'
    _description = 'Shipment Lines'
    _order = 'shipment_id, sequence'

    shipment_id = fields.Many2one('shipment')
    sequence = fields.Integer('#', compute='_compute_sequence', store=True)
    pack_type = fields.Many2one('shipment.package.type')
    pack_qty = fields.Integer('Cantidad')
    content_ids = fields.One2many('stock.move.shipment', 'shipment_line_id', string='Content')

    @api.depends('content_ids')
    def _compute_sequence(self):
        for rec in self:
            seq = 0
            for line in rec.shipment_id.line_ids:
                if line.content_ids:
                    seq = line.sequence = seq + 1
                else:
                    line.sequence = 0


class ShipmentPackageType(models.Model):
    _name = 'shipment.package.type'
    _description = 'Shipping Package Types'

    name = fields.Char('PackType', translate=True)
    description = fields.Char('Package Type Description')