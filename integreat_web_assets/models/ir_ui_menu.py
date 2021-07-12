# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, models, fields, _
from odoo.http import request

class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def load_menus(self, debug):
        menu_root = super(IrUiMenu, self).load_menus(debug)
        cids = request and request.httprequest.cookies.get('cids')
        if cids:
            cids = [int(cid) for cid in cids.split(',')]
        company = self.env['res.company'].browse(cids[0]) \
            if cids and all([cid in self.env.user.company_ids.ids for cid in cids]) \
            else self.env.user.company_id
        menu_root['background_image'] = bool(company.background_image)
        return menu_root
