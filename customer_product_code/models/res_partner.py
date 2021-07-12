# -*- coding: utf-8 -*-
from odoo import api, fields, models


class Partner(models.Model):
    _inherit = 'res.partner'
    _order = 'name'

    partner_code = fields.Char('Partner code')
    incoterm = fields.Many2one('account.incoterms', 'Incoterm')

    def _get_name(self):
        name = super()._get_name()
        if self.partner_code:
            name = '[%s] %s' % (self.partner_code, name)
        return name

    # override -> display_name is stored computed field... must depend on partner code, otherwise won't be recomputed
    @api.depends('is_company', 'name', 'parent_id.display_name', 'type', 'company_name', 'partner_code')
    def _compute_display_name(self):
        super()._compute_display_name()
