# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductAttributeUpdateWizardIntegreat(models.TransientModel):
    _name = 'product.attribute.update.wizard.integreat'
    _description = 'Product Attribute Update Wizard'

    template_id = fields.Many2one('product.template')

    def button_process(self):
        template = self.template_id
        self.unlink()
        if template.categ_id in (
            self.env.ref('integreat_sale_product_configurator.caja_troquelada'),
        ):
            for product in template.product_variant_ids:
                vals = {
                    'spec_calibre': product.product_template_attribute_value_ids[0].name,
                    'spec_papel': product.product_template_attribute_value_ids[1].name,
                    'spec_flauta': product.product_template_attribute_value_ids[2].name,
                    'spec_recub': product.product_template_attribute_value_ids[3].name,
                    'spec_ancho': int(product.product_template_attribute_value_ids[4].name),
                    'spec_largo': int(product.product_template_attribute_value_ids[5].name),
                }
                if product.categ_id == self.env.ref('integreat_sale_product_configurator.caja_troquelada'):
                    if product.spec_ancho_lamina == 0:
                        vals['spec_ancho_lamina'] = int(product.product_template_attribute_value_ids[4].name)
                    if product.spec_largo_lamina == 0:
                        vals['spec_largo_lamina'] = int(product.product_template_attribute_value_ids[5].name)
                product.write(vals)
        if template.categ_id in (
                self.env.ref('integreat_sale_product_configurator.lamina')
        ):
            for product in template.product_variant_ids:
                vals = {
                    'spec_calibre': product.prod[0].name,
                    'spec_papel': product.product_template_attribute_value_ids[1].name,
                    'spec_flauta': product.product_template_attribute_value_ids[2].name,
                    'spec_recub': product.product_template_attribute_value_ids[3].name,
                    'spec_ancho': int(product.product_template_attribute_value_ids[4].name),
                    'spec_largo': int(product.product_template_attribute_value_ids[5].name),
                }
                if product.categ_id == self.env.ref('integreat_sale_product_configurator.caja_troquelada'):
                    if product.spec_ancho_lamina == 0:
                        vals['spec_ancho_lamina'] = int(product.product_template_attribute_value_ids[4].name)
                    if product.spec_largo_lamina == 0:
                        vals['spec_largo_lamina'] = int(product.product_template_attribute_value_ids[5].name)
                product.write(vals)
