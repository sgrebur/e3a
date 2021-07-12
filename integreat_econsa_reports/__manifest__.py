# -*- coding: utf-8 -*-
# sgrebur InteGreat changed to V14
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'InteGreat Econsa Reports',
    'version': '14.0.1.0.1',
    'author': 'InteGreat',
    'license': 'AGPL-3',
    'category': 'Hidden',
    'depends': [
        'integreat_econsa_laminas',
        'integreat_stock_shipment',
        'integreat_mx_edi_extended',
        'integreat_sale_mrp_mtso'
    ],
    'data': [
        'report/l10n_mx_edi_report_payment.xml',
        'report/mrp_production_templates.xml',
        'report/purchase_order_templates.xml',
        'report/report_invoice.xml',
        'report/report_templates.xml',
        'report/shipment_templates.xml',
        'views/purchase_view.xml'
    ]
}
