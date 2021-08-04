# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class MrpPlanCheckAvailabilityWizard(models.TransientModel):
    _name = 'mrp.production.plan.wizard'
    _description = 'Mrp Check Availability when Planning'

    productions = fields.Many2many('mrp.production')

    def button_continue(self):
        return self.productions.with_context(with_no_stock=True).button_plan()
