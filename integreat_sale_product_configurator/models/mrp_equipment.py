# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpEquipmentType(models.Model):
    _name = "mrp.equipment.type"
    _description = 'MRP Equipment Type'

    type = fields.Selection([
        ('suaje', 'Suaje'),
        ('grabado', 'Grabado')
    ], string='Tipo ID', required=True)
    name = fields.Char('Categoria', required=True, index=True)
    sequence_id = fields.Many2one('ir.sequence')
    sequence_prefix = fields.Char(related='sequence_id.prefix')

    def create_sequence(self):
        for rec in self:
            if not rec.sequence_id:
                rec.sequence_id = self.env['ir.sequence'].create({
                    'name': 'mrp.equipment.' + rec.type + '.' + rec.name,
                    'code': 'mrp.equipment.' + rec.type + '.' + rec.name,
                    'implementation': 'standard',
                    'padding': 4
                })


class MrpEquipment(models.Model):
    _name = "mrp.equipment"
    _description = 'MRP Equipment'
    _inherit = ['mail.thread']

    name = fields.Char(string='No. Herramental', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    type_id = fields.Many2one('mrp.equipment.type')
    type_type = fields.Selection(string='Tipo', related='type_id.type', store=True)
    type_name = fields.Char(string='Categoria', related='type_id.name', store=True)
    description = fields.Char(string="Descripción")
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('ready', 'Inspeccionado'),
        ('blocked', 'Bloqueado'),
        ], string='Estado', readonly=True, copy=False, index=True, default='draft')
    default_location_id = fields.Many2one('stock.location', string='Ubicación por defecto')
    dest_location_id = fields.Many2one('stock.location', string='Ubicación actual')
    production_id = fields.Many2one('mrp.production', readonly=True)
    contact_name = fields.Char('Nombre contacto')
    observaciones = fields.Char('Observaciones', tracking=True)
    product_id = fields.Many2one('product.product')
    elem_por_herr = fields.Integer('Pzs/Golpe', default=1, required=True)
    elem_por_prod = fields.Integer('Pzs/Producto', default=1, required=True)
    ancho = fields.Integer(related='product_id.spec_ancho')
    largo = fields.Integer(related='product_id.spec_largo')
    bom_count = fields.Integer('Lista de materiales', compute='_compute_bom_count', compute_sudo=False)

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            type = vals.get('type_id', False)
            if type:
                equipment_type = self.env['mrp.equipment.type'].browse(type)
                if equipment_type:
                    vals['name'] = equipment_type.sequence_id.next_by_id() or 'Nuevo'
        return super(MrpEquipment, self).create(vals)

    def name_get(self):
        return [(rec.id, "[%s] %s - %s" % (rec.name, rec.description or '', rec.product_id.display_name or '')) for rec in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        equipment_ids = []
        if name:
            equipment_ids = self._search([('name', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        if not equipment_ids:
            equipment_ids = self._search([('description', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        if not equipment_ids:
            equipment_ids = self._search([('product_id', operator, name)] + args, limit=limit, access_rights_uid=name_get_uid)
        return equipment_ids

    def _compute_bom_count(self):
        for equipment in self:
            if equipment.type_name == 'suaje':
                equipment.bom_count = self.env['mrp.bom'].search_count([('suaje', '=', equipment.id)])
            elif equipment.type_name == 'grabado':
                equipment.bom_count = self.env['mrp.bom'].search_count([('grabado', '=', equipment.id)])
            else:
                equipment.bom_count = 0

    def action_view_bom(self):
        action = self.env["ir.actions.actions"]._for_xml_id("mrp.product_open_bom")
        action['domain'] = ['|', ('suaje', 'in', self.ids), ('grabado', 'in', self.ids)]
        return action

    def button_ready(self):
        self.write({'state': 'ready'})

    def button_block(self):
        self.write({'state': 'blocked'})

    def button_transfer_equipment(self):
        return {
            'name': 'Trasferir herramienta a otra ubicación',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.equipment.transfer.wizard',
            'view_id': self.env.ref('integreat_sale_product_configurator.mrp_equipment_transfer_wizard').id,
            'target': 'new',
            'context': {
                'default_equipment_id': self.id,
            }
        }
