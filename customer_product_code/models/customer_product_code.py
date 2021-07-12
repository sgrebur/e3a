# -*- coding: utf-8 -*-
###############################################################################
#
#   customer_product_code for Odoo
#   Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#   Copyright (C) 2016-today Geminate Consultancy Services (<http://geminatecs.com>).
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductCustomerCode(models.Model):
    _name = "product.customer.code"
    _description = "Add Code and Name of customer's product"
    _order = 'sequence, id'
    _rec_name = 'product_code'

    sequence = fields.Integer('Sequence', default=10)
    product_code = fields.Char(string='Customer Product Code', help="""This
        customer's product code will be used when searching into a request for
        quotation.""")
    product_name = fields.Char(string='Customer Product Name', help="""This
        customer's product name will be used when searching into a request for
        quotation.""")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id')
    partner_id = fields.Many2one('res.partner', string='Customer', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=False,
        default=lambda self: self.env.user.company_id)

    _sql_constraints = [
        ('unique_code', 'unique(product_id, company_id, partner_id)',
         'Product Code of customer must be unique'),
    ]

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            # hack to be able to use it on template w/o variant
            if val.get('product_tmpl_id', False):
                template = self.env['product.template'].search([('id', '=', val['product_tmpl_id'])])
                val['product_id'] = template.product_variant_ids[0].id
            # if not the company selected, we replace it
            if val.get('partner_id', False):
                val['partner_id'] = self.env['res.partner'].browse(val['partner_id']).commercial_partner_id.id \
                                    or val['partner_id']
        return super().create(vals)

