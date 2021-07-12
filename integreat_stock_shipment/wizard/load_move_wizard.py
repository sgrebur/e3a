# -*- coding: utf-8 -*-

from odoo import api, models, fields
from odoo.exceptions import UserError


class ShipmentLoadMoveWizard(models.TransientModel):
    _name = 'shipment.move.load.wizard'
    _description = 'Shipment Move Load Wizard'

    mixed = fields.Boolean('One mixed package')
    pack_type = fields.Many2one('shipment.package.type', default=lambda self: self.env.ref('integreat_stock_shipment.pallet'))
    shipment_id = fields.Many2one('shipment')
    line_ids = fields.One2many('shipment.move.load.wizard.line', 'wiz_id')

    def button_load_selected(self):
        lines = self.line_ids.filtered(lambda l: l.select == True)
        if lines:
            self.action_load(lines)
            self.unlink()
        else:
            raise UserError('¡Debe seleccionar líneas para combinar en una unidad de paquete!')

    def button_load_all(self):
        self.action_load(self.line_ids)
        self.unlink()

    def action_load(self, lines):
        shipment_line = False
        if self.mixed:
            shipment_line = self.env['shipment.line'].create({
                'shipment_id': self.shipment_id.id,
                'pack_type': self.pack_type.id,
                'pack_qty': 1,
            }).id
        for line in lines:
            if not self.mixed:
                shipment_line = self.env['shipment.line'].create({
                    'shipment_id': self.shipment_id.id,
                    'pack_type': line.pack_type.id,
                    'pack_qty': line.pack_qty,
                }).id
            self.env['stock.move.shipment'].create({
                'move_id': line.move_id.id,
                'shipment_id': self.shipment_id.id,
                'shipment_line_id': shipment_line,
                'qty': line.loaded_qty})

    def wizard_action(self, wiz_id):
        view_id = self.env.ref('integreat_stock_shipment.wizard_shipment_move_load_view').id
        return {
            'name': 'Crear Líneas de Transporte',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'shipment.move.load.wizard',
            'view_id': view_id,
            'target': 'new',
            'res_id': wiz_id
        }


class ShipmentLoadMoveWizardLine(models.TransientModel):
    _name = 'shipment.move.load.wizard.line'
    _description = 'Shipment Move Load Wizard'

    wiz_id = fields.Many2one('shipment.move.load.wizard')
    pack_type = fields.Many2one('shipment.package.type', default=lambda self: self.env.ref('integreat_stock_shipment.pallet'))
    pack_qty = fields.Integer('# Packages', default=1)
    select = fields.Boolean('Sel')
    move_id = fields.Many2one('stock.move')
    product_id = fields.Many2one(related='move_id.product_id')
    unloaded_qty = fields.Float(string='Restante', digits='Product Unit of Measure', default=0)
    loaded_qty = fields.Float(string='Cargada', digits='Product Unit of Measure')
    qty_to_load = fields.Float(related='move_id.qty_to_load')
    product_uom = fields.Many2one(related='move_id.product_uom')

    @api.onchange('loaded_qty')
    def _onchange_loaded_qty(self):
        unloaded_qty = self.qty_to_load - self.loaded_qty
        if unloaded_qty < 0:
            raise UserError('Debe ser menor que %s' % self.qty_to_load)
        else:
            self.unloaded_qty = unloaded_qty
