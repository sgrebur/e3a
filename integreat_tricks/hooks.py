# -*- coding: utf-8 -*-

from odoo import api, models, SUPERUSER_ID


def pre_init_hook_py(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    # reqs = env['purchase.request'].search([])
    # for req in reqs:
    #     if req.group_id and req.group_id.mrp_production_ids:
    #         for move in req.group_id.mrp_production_ids.mapped('move_raw_ids'):
    #             if move.product_id == req.product_id:
    #                 pur_line = req.line_ids.filtered(lambda x: x.product_id == move.product_id)
    #                 move.requested_purreq_line_id = pur_line[0]

    recs = env['stock.picking'].search([('state', 'not in', ['done', 'cancel']), ('location_id.name', 'in', ['INV', 'P1+2'])])
    for rec in recs.sudo():
        rec.location_id = rec.picking_type_id.default_location_src_id
