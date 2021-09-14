# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _


class LaminaSelection(models.TransientModel):
    _name = 'wizard.lamina.selection.product.select'
    _description = 'Add new product line'

    product_id = fields.Many2one('product.product', string='Lamina')
    wiz_id = fields.Many2one('wizard.lamina.selection')
    categ_id = fields.Many2one('product.category', compute='compute_fields')
    wiz_lamina_ids = fields.One2many('product.product', compute='compute_fields')
    papel = fields.Char(related='wiz_id.papel')
    flauta = fields.Char(related='wiz_id.flauta')
    recub = fields.Char(related='wiz_id.recub')
    ancho = fields.Integer(related='wiz_id.ancho')
    largo = fields.Integer(related='wiz_id.largo')

    @api.depends('wiz_id')
    def compute_fields(self):
        for wiz in self:
            wiz.categ_id = self.env.ref('integreat_sale_product_configurator.lamina').id
            wiz.wiz_lamina_ids = wiz.wiz_id.line_ids.product_id.ids

    def add_product_to_wizard(self):
        self.wiz_id.line_ids.create({
            'wizard_id': self.wiz_id.id,
            'line_group':  '0',
            'product_id': self.product_id.id,
            'location': self.wiz_id.location_id.id
        })
        action = self.wiz_id.lamina_wizard_action(self.wiz_id.id)
        self.unlink()
        return action
