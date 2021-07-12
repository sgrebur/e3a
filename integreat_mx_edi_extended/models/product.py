# coding: utf-8

from odoo import api, fields, models, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    l10n_mx_edi_clave_search_pattern = fields.Char(string='ClaveProdServ Import XML',
        help='Full code or begins with. Can be a list separated by comma')


class Product(models.Model):
    _inherit = 'product.product'

    product_unspsc_code_id = fields.Many2one('product.unspsc.code', 'UNSPSC Clave Producto',
        compute='_compute_unspsc_code', store=True, readonly=False, domain=[('applies_to', '=', 'product')],
        help='The UNSPSC code related to this product VARIANT.  Used for edi in Colombia, Peru and Mexico')

    @api.depends('product_tmpl_id')
    def _compute_unspsc_code(self):
        for product in self:
            product.product_unspsc_code_id = product.product_tmpl_id.unspsc_code_id


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_unspsc_code_id = fields.Many2one('product.unspsc.code', 'UNSPSC Clave Producto',
         domain=[('applies_to', '=', 'product')], compute='_compute_unspsc_code', store=True, readonly=False)

    @api.depends('product_id')
    def _compute_unspsc_code(self):
        for line in self:
            if line.product_id:
                line.product_unspsc_code_id = line.product_id.product_unspsc_code_id
            else:
                line.product_unspsc_code_id = False
