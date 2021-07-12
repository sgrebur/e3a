# -*- coding: utf-8 -*-
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'InteGreat Tricks',
    'version': '14.0.1.0.1',
    'author': 'InteGreat',
    'website': 'https://odoo-community.org/',
    'license': 'AGPL-3',
    'category': 'Product',
    'depends': [
        'base', 'stock', 'purchase_request'
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/ir_model_data_wizard.xml',
    ],
    'installable': True,
    # 'pre_init_hook': 'pre_init_hook_py',
}
