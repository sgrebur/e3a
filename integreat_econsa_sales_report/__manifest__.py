# -*- coding: utf-8 -*-
# sgrebur InteGreat changed to V14
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Lamina Econsa Sale Flow Report',
    'version': '14.0.1.0.1',
    'author': 'InteGreat',
    'website': 'https://odoo-community.org/',
    'license': 'AGPL-3',
    'category': 'Product',
    'depends': [
        'integreat_econsa_laminas',
    ],
    'data': [
        'wizard/sales_flow_report_views.xml',
        'security/ir.model.access.csv'
    ],
    'installable': True
}
