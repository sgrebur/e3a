# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    is_model = fields.Boolean('Is model?')
    suaje = fields.Many2one('mrp.equipment', domain="[('type_type', '=' , 'suaje')]", string='Suaje')
    grabado = fields.Many2one('mrp.equipment', domain="[('type_type', '=', 'grabado')]", string='Grabado')

    @api.onchange('suaje')
    def _onchange_suaje(self):
        for bom in self:
            if bom.suaje and bom.suaje.elem_por_herr > 0:
                bom.product_qty = bom.suaje.elem_por_herr
                self.env.user.notify_info(message='Pzs/Herr se ha cambiado de suaje seleccionado')

    def write(self, values):
        if values.get('suaje'):
            suaje = self.env['mrp.equipment'].browse(values.get('suaje'))
            if not suaje.product_id:
                suaje.write({'product_id': self.product_id.id})
        if values.get('grabado'):
            grabado = self.env['mrp.equipment'].browse(values.get('grabado'))
            if not grabado.product_id:
                grabado.write({'product_id': self.product_id.id})
        if values.get('sequence') and not self.product_id:
            if values['sequence'] < 1000000:
                values['sequence'] += 1000000
        return super().write(values)

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if values.get('sequence') and not self.product_id:
                if values['sequence'] < 1000000:
                    values['sequence'] += 1000000
        return super().create(vals_list)


class MrpBom(models.Model):
    _inherit = "mrp.bom.line"

    route_id = fields.Many2one('stock.location.route', 'Suministro Especial')
