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
        'integreat_mrp_process',
        'product',
        'sale',
        'mrp_workorder',
        'customer_product_code',
        'web_notify'
    ],
    'data': [
        'data/product_templates.xml',
        'views/mrp_bom_views.xml',
        'views/mrp_equipment.xml',
        'views/mrp_production_views.xml',
        'views/product_views.xml',
        'wizard/mrp_workorder_record_qty.xml',
        'wizard/mrp_equipment_transfer_wizard.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
