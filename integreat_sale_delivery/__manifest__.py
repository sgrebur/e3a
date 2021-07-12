# Copyright InteGreat
# by greburs
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "InteGreat Sale Order Delivery",
    "summary": "Sale Order Delivery Enhancements",
    "author": "greburs, InteGreat",
    "website": "https://integreat.de",
    "category": "uncategorized",
    "version": "14.0.1.0.1",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "sale",
        "stock",
        "sale_stock",
        "customer_product_code"
    ],
    "data": ["views/sale_order_views.xml"],
}
