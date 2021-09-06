# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'EDI for Mexico (Advanced Features)',
    'version': '0.1',
    'category': 'Hidden',
    'description': """EDI for Mexico (Advanced Features: Leyendas, Import Vendor Bill from XML)""",
    'depends': ['base', 'account', 'sale', 'l10n_mx_edi_extended'],
    'data': [
        'data/3.3/cfdi.xml',
        'data/product_serv_credit_note.xml',
        'views/account_move_view.xml',
        'views/account_payment_view.xml',
        'views/product_view.xml',
        'views/res_partner_view.xml',
        'views/sale_view.xml'
    ],
    'installable': True,
    'auto_install': False,
}
