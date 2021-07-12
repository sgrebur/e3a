# -*- coding: utf-8 -*-
# sgrebur InteGreat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'InteGreat Shipment Module',
    'version': '14.0.1.0.1',
    'author': 'InteGreat',
    'website': 'https://integreat.de/',
    'license': 'AGPL-3',
    'category': 'Stock',
    'depends': [
        'sale_stock', 'integreat_sale_mrp_mtso'
    ],
    'data': [
        'data/data.xml',
        'views/picking_views.xml',
        'views/shipment_views.xml',
        'wizard/load_move_wizard_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}
