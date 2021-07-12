# Copyright InteGreat
# by greburs
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "InteGreat Sale Replenishment",
    "summary": "InteGreat Sale Replenishment from Stock, otherwise Make-To-Order",
    "author": "greburs, InteGreat",
    "website": "https://integreat.de",
    "category": "uncategorized",
    "version": "14.0.1.0.1",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "sale_purchase_stock",
        "sale_mrp",
        "purchase_mrp",
        "purchase_request",
        "integreat_sale_product_configurator",
        "integreat_sale_delivery",
    ],
    "data": [
        "views/mrp_views.xml",
        "views/product_views.xml",
        "views/sale_views.xml",
        "views/stock_views.xml",
        "security/ir.model.access.csv"
    ],
}
