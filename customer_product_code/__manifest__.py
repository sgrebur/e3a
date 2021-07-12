# -*- coding: utf-8 -*-
###############################################################################
#
#   customer_product_code for Odoo
#   Copyright (C) 2004-today OpenERP SA (<http://www.openerp.com>)
#   Copyright (C) 2016-today Geminate Consultancy Services (<http://geminatecs.com>).
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as
#   published by the Free Software Foundation, either version 3 of the
#   License, or (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
{
    "name": "Customers Product Code", 
    "version": "14.9.1.1",
    "author": "Geminate Consultancy Services", 
    "category": "Product", 
    "description": """This module will add feature to manage products having customer specific code and name 
        and that will be used for sales process.""",
    "website": "http://www.geminatecs.com", 
    "license": "Other proprietary", 
    "depends": [
        "base", "sale_management", "account", "stock"
    ], 
    "demo": [], 
    "data": [
        "security/customer_product_code_security.xml", 
        "security/ir.model.access.csv",
        'views/res_parnter_views.xml',
        "views/product_product_view.xml",
        "views/customer_product_code_view.xml" 
    ],
    "images": ['static/description/icon.png'],
    "installable": True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
