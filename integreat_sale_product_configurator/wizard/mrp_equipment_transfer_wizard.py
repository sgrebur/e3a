# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class MrpEquipmentTransferWizard(models.TransientModel):
    _name = 'mrp.equipment.transfer.wizard'
    _description = 'Mrp Equipment Transfer Wizard'

    production_transfer = fields.Boolean(default=False)
    block_transfer = fields.Boolean(default=False)
    production_id = fields.Many2one('mrp.production', string='OP requerida')
    equipment_id = fields.Many2one('mrp.equipment', string='Herramental')
    default_location_id = fields.Many2one(related='equipment_id.default_location_id', string='Ubicación por defecto')
    dest_location_id = fields.Many2one(related='equipment_id.dest_location_id', string='Ubicación actual')
    actual_production_id = fields.Many2one(related='equipment_id.production_id', string='OP actual')
    new_location_id = fields.Many2one('stock.location', string='Ubicación destino', required=True, domain=[('usage', '!=', 'view')])
    contact_name = fields.Char('Nombre contacto')
    observaciones = fields.Char('Observaciones')
    message = fields.Char(compute='compute_message')

    @api.onchange('equipment_id', 'new_location_id')
    def compute_message(self):
        self.message = False
        if self.equipment_id:
            if self.actual_production_id and self.production_transfer and self.new_location_id and self.new_location_id == self.dest_location_id:
                self.message = 'La herramienta ya están en uso en la misma ubicación y será asignado a este OP.'
            if self.new_location_id and self.dest_location_id and self.new_location_id != self.dest_location_id and self.dest_location_id != self.default_location_id:
                self.message = 'La herramienta está en otro lugar.\n' \
                               'No se puede transferir hasta que no se devuelva a su ubicación por defecto.'
                self.block_transfer = True
            if self.equipment_id.state == 'blocked':
                self.message = 'La herramienta está bloqueada.'
                self.block_transfer = True

    def button_book_production_transfer(self):
        if self.equipment_id.type_type == 'suaje':
            if self.actual_production_id:
                self.actual_production_id.write({'suaje_transfer_state': False})
            self.production_id.write({'suaje_transfer_state': 'done'})
        if self.equipment_id.type_type == 'grabado':
            if self.actual_production_id:
                self.actual_production_id.write({'grabado_transfer_state': False})
            self.production_id.write({'grabado_transfer_state': 'done'})
        self.equipment_id.write({
            'production_id': self.production_id,
            'dest_location_id': self.new_location_id,
            'contact_name': self.contact_name,
            'observaciones': self.observaciones,
        })
        self.unlink()

    def button_book_location_transfer(self):
        self.equipment_id.write({
            'dest_location_id': self.new_location_id,
            'contact_name': self.contact_name,
            'observaciones': self.observaciones,
        })
        self.unlink()
