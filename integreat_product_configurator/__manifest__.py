# -*- coding: utf-8 -*-
# sgrebur InteGreat changed to V14
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'InteGreat Product Configurator',
    'version': '14.0.1.0.1',
    'author': 'InteGreat',
    'website': 'https://odoo-community.org/',
    'license': 'AGPL-3',
    'category': 'Product',
    'depends': [
        'product',
        'product_variant_default_code',
        'sale_product_configurator',
        'integreat_sale_product_configurator',
        'purchase',
        'integreat_econsa_laminas',
        'l10n_mx_edi',
        'web'
    ],
    'data': [
        'wizard/attribute_product_update.xml',
        'wizard/product_configurator_views.xml',
        'views/assets.xml',
        'views/product_view.xml',
        'views/purchase_view.xml',
        'views/sale_view.xml',
        'security/ir.model.access.csv',
    ],
    'qweb': [
        'static/src/xml/template.xml',
    ],
    'installable': True,
}
