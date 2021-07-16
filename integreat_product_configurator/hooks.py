# -*- coding: utf-8 -*-

from odoo import api, models, SUPERUSER_ID


def pre_init_hook_py(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # we add domain to exclude is_model from all possible actions
    recs = env['ir.actions.act_window'].sudo().search([('res_model', 'in', ['product.template', 'product.product'])])
    for rec in recs.sudo():
        if rec.domain:
            rec.domain += [('is_model', '=', False)]
        else:
            rec.domain = [('is_model', '=', False)]


def uninstall_hook_py(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # we remove domains related to is_model
    recs = env['ir.actions.act_window'].sudo().search([('res_model', 'in', ['product.template', 'product.product'])])
    for rec in recs.sudo():
        rec.domain = False