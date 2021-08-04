# -*- coding: utf-8 -*-
# sgrebur InteGreat changed to V14
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Lamina Selector for Econsa',
    'version': '14.0.1.0.1',
    'author': 'InteGreat',
    'website': 'https://odoo-community.org/',
    'license': 'AGPL-3',
    'category': 'Product',
    'depends': [
        'mrp_workorder',
        'integreat_sale_product_configurator',
        'integreat_sale_mrp_mtso',
        'web_kanban_gauge',
        'sale_stock'
    ],
    'data': [
        'data/data.xml',
        'views/mrp_production_views.xml',
        'views/product_views.xml',
        'wizard/lamina_selector_views.xml',
        'wizard/mrp_purreq_wizard.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True
}
