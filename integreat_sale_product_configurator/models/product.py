# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class ProductConfigurationIntegreat(models.Model):
    _name = 'product.configuration.integreat'
    _description = 'Custom Product Configuration'
    _order = 'sequence, name'

    name = fields.Char(string='Estilo')
    sequence = fields.Integer('Sequencia', default=10)
    product_model_ids = fields.Many2many('product.product', string='Product Models where apply', domain="[('is_model', '=', True)]")
    margin_target = fields.Float('Margin')
    mm_tolerancia = fields.Integer('MM Tolerancia', default=0)
    formula_ancho = fields.Char('Ancho Lamina')
    formula_largo = fields.Char('Largo Lamina')
    quotation_terms = fields.Text(string='Default Terms and Conditions', translate=True)

    _sql_constraints = [
        ('name_uniq', 'UNIQUE (name)', '¡La definición de estilo debe ser única!')
    ]

    @api.constrains('formula_ancho', 'formula_largo', 'quotation_terms')
    def _check_validity(self):
        for rec in self:
            l = w = h = 100
            try:
                eval(rec.formula_ancho)
                eval(rec.formula_largo)
            except:
                raise ValidationError('Su fórmula de cálculo no se puede evaluar. ¡Por favor, compruebe!')
            if rec.quotation_terms:
                y = rec.quotation_terms.find('XXX')
                z = rec.quotation_terms.find('FOB')
                if y < 0 or z < 0:
                    raise ValidationError('Las expresiones "XXX" y "FOB"'
                                          'deben usarse en los Términos y condiciones \n'
                                          'para actualizar automáticamente los detalles '
                                          'de la moneda y de logistica.')


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"
    # if you change this _order, keep it in sync with the method
    # `_sort_key_variant` in `product.template'
    # _order = 'attribute_id, sequence, id'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', False):
                try:
                    vals['sequence'] = int(vals['name'])
                except:
                    pass
        return super().create(vals_list)


class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    def name_get(self):
        """Override because in general the name of the value is confusing if it
        is displayed without the name of the corresponding attribute.
        Eg. on product list & kanban views, on BOM form view

        However during variant set up (on the product template form) the name of
        the attribute is already on each line so there is no need to repeat it
        on every value.
        """
        return [(value.id, value.name) for value in self]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_model_id = fields.Many2one('product.product', string='Modelo', domain="[('is_model', '=', True)]")
    is_model = fields.Boolean('Is model?')
    tmpl_calibre = fields.Char('Calibre ECT (L)')
    tmpl_papel = fields.Char('Liner (L)')
    tmpl_flauta = fields.Char('Flauta (L)')
    tmpl_recub = fields.Char('Recubrimiento (L)')
    tmpl_origen = fields.Selection([('NAL', 'NAL'), ('IND', 'IND'), ('HAZ', 'HAZ')], string='Origen', default='NAL')

    def write(self, values):
        if self.env.user.id not in [1, 2] and not self.env.su:
            blocked_categs = [self.env.ref('integreat_sale_product_configurator.caja_troquelada').id,
                                self.env.ref('integreat_sale_product_configurator.lamina').id]
            for tmpl in self:
                if tmpl.categ_id.id in blocked_categs or \
                        (values.get('categ_id', False) and values.get('categ_id') in blocked_categs):
                    raise ValidationError('¡No está autorizado para crear o editar '
                                          'productos de la categoría Lámina o Caja Troquelada!')
        return super().write(values)

    @api.model_create_multi
    def create(self, vals_list):
        if self.env.user.id not in [1, 2] and not self.env.su:
            for values in vals_list:
                blocked_categs = [self.env.ref('integreat_sale_product_configurator.caja_troquelada').id,
                                    self.env.ref('integreat_sale_product_configurator.lamina').id]
                if values.get('categ_id', False) and values.get('categ_id') in blocked_categs:
                    raise ValidationError('¡No está autorizado para crear o editar '
                                          'productos de la categoría Lámina o Caja Troquelada!')
        return super().create(vals_list)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    product_docs = fields.Many2many('ir.attachment', relation='m2m_ir_attachment_product_product_doc_rel',
        column1='m2m_id', column2='attachment_id', string='Archivos Producto')
    specification_docs = fields.Many2many('ir.attachment', relation='m2m_ir_attachment_product_specification_doc_rel',
        column1='m2m_id', column2='attachment_id', string='Archivos Especificaciones')
    tinta_color = fields.Integer('Color', default=0)
    spec_calibre = fields.Char('Calibre ECT')
    spec_papel = fields.Char('Liner')
    spec_flauta = fields.Char('Flauta')
    spec_recub = fields.Char('Recubrimiento')
    spec_ancho = fields.Integer('Ancho', compute='_compute_spec_fields', store=True)
    spec_largo = fields.Integer('Largo', compute='_compute_spec_fields', store=True)
    spec_alto = fields.Integer('Alto', compute='_compute_spec_fields', store=True)
    spec_origen = fields.Selection([('NAL', 'NAL'), ('IND', 'IND'), ('HAZ', 'HAZ')], string='Origen', default='NAL')
    spec_marca1 = fields.Char('Marca 1')
    spec_marca2 = fields.Char('Marca 2')
    spec_marca3 = fields.Char('Marca 3')
    spec_ancho_lamina = fields.Integer('Ancho Lamina', default=0)
    spec_largo_lamina = fields.Integer('Largo Lamina', default=0)
    uom_size = fields.Selection([('mm', 'mm'), ('in', 'in')], default='mm')
    ancho_uom = fields.Integer('Ancho Interno', default=0)
    largo_uom = fields.Integer('Largo Interno', default=0)
    alto_uom = fields.Integer('Alto Interno', default=0)

    _sql_constraints = [
        ('default_code_uniq', 'UNIQUE (default_code)', '¡La referencia interna del producto debe ser unico !')
    ]

    @api.depends('product_template_attribute_value_ids', 'uom_size', 'ancho_uom', 'largo_uom', 'alto_uom')
    def _compute_spec_fields(self):
        for p in self:
            if p.product_template_attribute_value_ids and \
                    p.categ_id == self.env.ref('integreat_sale_product_configurator.lamina'):  # only in case of Laminas
                p.spec_ancho = int(p.product_template_attribute_value_ids[0].name)
                p.spec_largo = int(p.product_template_attribute_value_ids[1].name)
                p.spec_alto = 0
            else:
                if p.uom_size == 'in':
                    p.spec_ancho = int(float_round(p.ancho_uom * 25.4, precision_digits=0))
                    p.spec_largo = int(float_round(p.largo_uom * 25.4, precision_digits=0))
                    p.spec_alto = int(float_round(p.alto_uom * 25.4, precision_digits=0))
                else:
                    p.spec_ancho = p.ancho_uom
                    p.spec_largo = p.largo_uom
                    p.spec_alto = p.alto_uom

    @api.constrains('spec_ancho_lamina', 'spec_largo_lamina')
    def _check_lamina_ancho_largo(self):
        for rec in self:
            if rec.spec_ancho > 0 and rec.spec_ancho_lamina > 0:
                if rec.spec_ancho_lamina < rec.spec_ancho:
                    raise ValidationError('¡Ancho lámina debe ser mayor que el ancho del producto!')
            if rec.spec_largo > 0 and rec.spec_largo_lamina > 0:
                if rec.spec_largo_lamina < rec.spec_largo:
                    raise ValidationError('¡Largo lámina debe ser mayor que el largo del producto!')


class PricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    applied_on = fields.Selection([
        ('3_global', 'All Products'),
        ('2_product_category', 'Product Category'),
        ('1_product', 'Product'),
        ('0_product_variant', 'Product Variant')], "Apply On",
        default='0_product_variant', required=True,
        help='Pricelist Item applicable on selected option')
