# -*- coding: utf-8 -*-
# sgrebur InteGreat

from odoo import api, fields, models, _
from odoo.tools import float_round
from odoo.exceptions import ValidationError
from datetime import date


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_lamina_required = fields.Boolean('No permita la producción sin una selección de lámina')
    list_price = fields.Float(default=0.0)
    seller_ids_template = fields.One2many('product.supplierinfo', 'show_on_template_id')


class ProductProduct(models.Model):
    _inherit = "product.product"

    surface = fields.Float('m2', digits=(16, 6), compute='_compute_spec_fields', store=True)
    seller_ids_product = fields.One2many('product.supplierinfo', 'show_on_product_id')

    # return supplierinfo only when is not
    def _prepare_sellers(self, params=False):
        return super()._prepare_sellers(params=params).filtered(lambda s: s.is_lamina_price is False)

    # OVERRIDE extend from integreat_sale_product_configurator
    @api.depends('product_template_attribute_value_ids')
    def _compute_spec_fields(self):
        super()._compute_spec_fields()
        for product in self:
            product.surface = product.spec_ancho * product.spec_largo / 1000000
            if product.surface > 0 and \
                    product.categ_id == self.env.ref('integreat_sale_product_configurator.lamina'):
                infos = self.env['product.supplierinfo'].search([
                    ('product_tmpl_id', '=', product.product_tmpl_id.id),
                    ('product_id', '=', False),
                    ('is_lamina_price', '=', True)
                ])
                infos.create_update_lamina_prices(products=product)


class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    is_lamina_price = fields.Boolean('Precio Lámina pro m2')
    surface = fields.Float(related='product_id.surface')
    price_per_m2 = fields.Float('Precio/m2', digits='Product Price')
    categ_id = fields.Many2one(related='product_tmpl_id.categ_id')
    show_on_template_id = fields.Many2one('product.template', 'Relevant for Template', compute='_compute_relevance', store=True)
    show_on_product_id = fields.Many2one('product.product', 'Relevant for Variant', compute='_compute_relevance', store=True)

    @api.depends('is_lamina_price', 'product_tmpl_id.product_variant_ids', 'product_tmpl_id.seller_ids.price', 'product_id')
    def _compute_relevance(self):
        for rec in self:
            if rec.product_tmpl_id and (not rec.product_id or rec.product_tmpl_id.product_variant_count <= 1):
                rec.show_on_template_id = rec.product_tmpl_id
                rec.show_on_product_id = False
            elif rec.product_id:
                rec.show_on_template_id = False
                rec.show_on_product_id = rec.product_id
            else:
                rec.show_on_template_id = False
                rec.show_on_product_id = False

    @api.constrains('is_lamina_price', 'name', 'product_tmpl_id', 'product_id', 'date_start', 'date_end', 'min_qty', 'price')
    def _check_overlapping(self):
        for rec in self:
            other_infos = self.env['product.supplierinfo'].search([
                ('id', 'not in', self.ids),
                ('name', '=', rec.name.id or False),
                ('product_tmpl_id', '=', rec.product_tmpl_id and rec.product_tmpl_id.id or False),
                ('product_id', '=', rec.product_id and rec.product_id.id or False),
                ('min_qty', '=', rec.min_qty),
            ])
            if other_infos:
                for other in other_infos:
                    latest_start = max(rec.date_start or date(1, 1, 1), other.date_start or date(1, 1, 1))
                    earliest_end = min(rec.date_end or date(9999, 12, 31), other.date_end or date(9999, 12, 31))
                    delta = (earliest_end - latest_start).days + 1
                    overlap = max(0, delta)
                    if overlap > 0:
                        raise ValidationError('Hay una entrada de precio superpuesta. \n'
                                              'Modifíquelo o reduzca su validez.')
            if not rec.is_lamina_price and not rec.product_id:
                raise ValidationError('Cuando no se trata de un precio de lámina pro m2, \n'
                                      'debe seleccionar la variante de producto \n'
                                      'incluso si es la misma que la plantilla de producto.')
            if rec.product_id and rec.categ_id == self.env.ref('integreat_sale_product_configurator.lamina') \
                    and rec.price_per_m2 > 0 and not self._context.get('is_allowed', False):
                raise ValidationError('No se permite cambiar un precio de lámina calculado pro m2. \n'
                                      'En su lugar, puede cambiar el precio en la plantilla de producto.')
            if rec.price <= 0.0:
                raise ValidationError('¡El precio debe ser superior a cero!')
    
    @api.onchange('product_id')
    def _onchange_product_id_template(self):
        for info in self:
            if info.product_id:
                info.product_tmpl_id = info.product_id.product_tmpl_id

    @api.model_create_multi
    def create(self, vals_list):
        infos = super().create(vals_list)
        infos.create_update_lamina_prices()
        return infos

    def write(self, vals):
        infos = super().write(vals)
        self.create_update_lamina_prices()
        return infos
    
    def unlink(self):
        for info in self:
            if info.product_id and info.categ_id == self.env.ref('integreat_sale_product_configurator.lamina') \
                    and info.price_per_m2 > 0 and info.price > 0 and not self._context.get('is_allowed', False):
                raise ValidationError('No se permite eliminar un precio de lámina calculado pro m2. \n'
                                      'En su lugar, puede eliminar el precio de la plantilla de producto.')
            if not info.product_id and info.is_lamina_price:
                infos_delete = self.env['product.supplierinfo'].search([
                    ('name', '=', info.name.id),
                    ('product_id', 'in', info.product_tmpl_id.product_variant_ids.ids),
                    ('price_per_m2', '>', 0)
                ])
                infos_delete.with_context(is_allowed=True).unlink()
        return super().unlink()

    def create_update_lamina_prices(self, products=False):
        for info in self:
            if not info.product_id and info.is_lamina_price:
                new_info_list = []
                if not products:
                    products = info.product_tmpl_id.product_variant_ids.filtered(lambda x: x.surface > 0)
                for product in products:
                    prod_info = self.env['product.supplierinfo'].search(
                        [('name', '=', info.name.id), ('product_id', '=', product.id), ('price_per_m2', '>', 0)], limit=1)
                    if prod_info:
                        prod_info.with_context(is_allowed=True).write({
                            'product_name': info.product_name,
                            'product_code': info.product_code,
                            'price': float_round(product.surface * info.price, precision_digits=6),
                            'price_per_m2': info.price,
                            'company_id': info.company_id,
                            'currency_id': info.currency_id.id,
                            'date_start': info.date_start,
                            'date_end': info.date_end,
                            'delay': info.delay,
                        })
                    else:
                        new_info = {
                            'name': info.name.id,
                            'product_name': info.product_name,
                            'product_code': info.product_code,
                            'price': float_round(product.surface * info.price, precision_digits=6),
                            'price_per_m2': info.price,
                            'company_id': info.company_id.id,
                            'currency_id': info.currency_id.id,
                            'date_start': info.date_start,
                            'date_end': info.date_end,
                            'product_id': product.id,
                            'product_tmpl_id': info.product_tmpl_id.id,
                            'delay': info.delay,
                        }
                        new_info_list.append(new_info)
                if new_info_list:
                    self.env['product.supplierinfo'].with_context(is_allowed=True).create(new_info_list)
