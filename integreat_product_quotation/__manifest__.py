# -*- coding: utf-8 -*-
# sgrebur InteGreat

{
    'name': 'InteGreat Econsa Cotizador',
    'version': '14.0.1.0.1',
    'author': 'InteGreat',
    'website': 'https://odoo-community.org/',
    'license': 'AGPL-3',
    'category': 'Product',
    'depends': [
        'integreat_product_configurator',
        'integreat_econsa_laminas'
    ],
    'data': [
        'views/product_quotation_views.xml',
        'views/quotation_report.xml',
        'wizard/lamina_selector_views.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/mail_data.xml',
    ],
    'installable': True,
}
