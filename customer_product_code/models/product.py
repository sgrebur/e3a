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

from odoo import _, api, fields, models, SUPERUSER_ID
import copy


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_customer_code_ids = fields.One2many('product.customer.code', 'product_tmpl_id', 'Customer Code')

    # # OVERRIDE default code extended with customer code
    # @api.depends('product_variant_ids', 'product_variant_ids.default_code')
    # def _compute_default_code(self):
    #     unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
    #     for template in unique_variants:
    #         template.default_code = template.product_variant_ids.default_code
    #         template.product_customer_code_ids = template.product_variant_ids.product_customer_code_ids
    #     for template in (self - unique_variants):
    #         template.default_code = False
    #         template.product_customer_code_ids = False
    #
    # # OVERRIDE default code extended with customer code
    # def _set_default_code(self):
    #     for template in self:
    #         if len(template.product_variant_ids) == 1:
    #             template.product_variant_ids.default_code = template.default_code
    #             template.product_variant_ids.default_code = template.product_customer_code_ids


class ProductProduct(models.Model):
    _inherit = "product.product"

    product_customer_code_ids = fields.One2many('product.customer.code', 'product_id', 'Customer Codes')

    def _product_partner_ref(self):
        res = {}
        for p in self:
            data = self._get_partner_code_name(p, self._context.get('partner_id', None))
            if not data['code']:
                data['code'] = p.code
            if not data['name']:
                data['name'] = p.name
            res[p.id] = (data['code'] and ('['+data['code']+'] ') or '') + (data['name'] or '')
            p.partner_ref = res[p.id]
        return res

    def _get_partner_code_name(self, product, partner_id):
        if self._context.get('type', False) == 'in_invoice':
            for supinfo in product.seller_ids:
                if supinfo.name.id == partner_id:
                    return {'code': supinfo.product_code or product.default_code, 'name': supinfo.product_name or product.name}
        else:
            for buyinfo in product.product_customer_code_ids:
                if buyinfo.partner_id.id == partner_id:
                    return {'code': buyinfo.product_code or product.default_code, 'name': buyinfo.product_name or product.name}
        res = {'code': product.default_code, 'name': product.name}
        return res
 
    partner_ref = fields.Char(compute='_product_partner_ref', string='Customer ref')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if not default:
            default = {}
        default['product_customer_code_ids'] = False
        res = super(ProductProduct, self).copy(default=default)
        return res

    def name_get(self):
        # TDE: this could be cleaned a bit I think

        def _name_get_custom(d):
            name = d.get('name', '')
            code = self._context.get('display_default_code', True) and d.get('default_code', False) or False
            if code:
                if d.get('partner_code'):
                    name = '[%s] %s (%s)' % (d['partner_code'], name, code)
                else:
                    name = '(%s) %s' % (code, name)
            return (d['id'], name)
 
        partner_id = self._context.get('partner_id')
        if partner_id:
            partner_ids = [partner_id, self.env['res.partner'].browse(partner_id).commercial_partner_id.id]
        else:
            partner_ids = []
# 
#         # all user don't have access to seller and partner
#         # check access and use superuser
        self.check_access_rights("read")
        self.check_access_rule("read")
 
        result = []
        for product in self.sudo():
            # display only the attributes with multiple possible values on the template
            # variable_attributes = product.attribute_line_ids.filtered(lambda l: len(l.value_ids) > 1).mapped('attribute_id')
            # variant = product.product_template_attribute_value_ids._variant_name(variable_attributes)
            # variant = product.product_template_attribute_value_ids._get_combination_name()

            # if product.default_code:
            #     name = "[%s] %s" % (product.default_code, product.name) or product.name
            # else:
            #     name = product.name
            sellers = []
            buyers = []
            if partner_ids:
                sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and (x.product_id == product)]
                if not sellers:
                    sellers = [x for x in product.seller_ids if (x.name.id in partner_ids) and not x.product_id]
                buyers = [x for x in product.product_customer_code_ids if (x.partner_id.id == partner_id) and (x.product_id == product)]
            else:
                buyers = [x for x in product.product_customer_code_ids if (x.product_id == product)]
            if sellers:
                for s in sellers:
                    mydict = {
                        'id': product.id,
                        'name': s.product_name or product.name,
                        'default_code': product.default_code,
                        'partner_code': s.product_code or False
                    }
                    temp = _name_get_custom(mydict)
                    if temp not in result:
                        result.append(temp)
            elif buyers:
                for b in buyers:
                    mydict = {
                        'id': product.id,
                        'name': b.product_name or product.name,
                        'default_code': product.default_code,
                        'partner_code': b.product_code,
                    }
                    result.append(_name_get_custom(mydict))
            else:
                mydict = {
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code,
                    'partner_code': False
                }
                result.append(_name_get_custom(mydict))
        return result
   
    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        if not args:
            args = []
        cust_args = copy.deepcopy(args)
        for arg in cust_args:
            if isinstance(arg, tuple):
                arg = list(arg)
            if isinstance(arg, list):
                arg[0] = 'product_id.' + arg[0]
        res = []
        if not self._context:
            context = {}
        product_customer_code_obj = self.env['product.customer.code']
        if not res:
            ids = []
            partner_id = self._context.get('partner_id', False)
            # search partner code
            if partner_id:
                id_prod_code = product_customer_code_obj.search([
                    ('product_code', 'ilike', name), ('partner_id', '=', partner_id)
                ] + cust_args, limit=limit)
            else:
                id_prod_code = product_customer_code_obj.search([
                    ('product_code', 'ilike', name)
                ] + cust_args, limit=limit)
            # search additionally partner description
            if partner_id:
                id_prod_code += product_customer_code_obj.search([
                    ('product_name', 'ilike', name), ('partner_id', '=', partner_id)
                ] + cust_args, limit=limit)
            else:
                id_prod_code += product_customer_code_obj.search([
                    ('product_name', 'ilike', name)
                ] + cust_args, limit=limit)
            if id_prod_code:
                for ppu in id_prod_code:
                    ids.append(ppu.product_id.id)
            if ids:
                res = self._search([('id', 'in', ids)], limit=limit)
            if limit > len(res):
                limit -= len(res)
        args = list(filter(lambda x: x[0] != 'product_customer_code_ids.partner_id', args))
        if res:
            res = list(res)
        res += list(super()._name_search(name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid))
        return res
