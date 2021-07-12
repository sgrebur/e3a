# -*- coding: utf-8 -*-

from odoo import fields, models, api
from odoo.osv.expression import AND
from odoo.tools import float_round


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    quotation_id = fields.Many2one('product.quotation.integreat', string='Product Quotations', check_company=True)

    def _bom_quotation_find(self, product_tmpl=None, product=None, company_id=False, bom_type='quotation', quotation_id=False):
        domain = self._bom_find_domain(product_tmpl=product_tmpl, product=product, company_id=company_id, bom_type=bom_type)
        if quotation_id:
            domain = AND([domain, [('quotation_id', '=', quotation_id.id)]])
            return self.search(domain, order='sequence, product_id', limit=1)
        else:
            return self.env['mrp.bom']


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    quotation_id = fields.Many2one('product.quotation.integreat', related='bom_id.quotation_id', store=True)
    quot_currency = fields.Many2one('res.currency', related='quotation_id.currency_id')
    quot_qty = fields.Float('Ctd requerida', digits='Product Unit of Measure', compute='_compute_quot')
    quot_surface = fields.Float('m2', digits=(16, 6), compute='_compute_quot')
    quot_free = fields.Float(related='product_id.free_qty', string='Ctd libre')
    quot_unit_cost = fields.Float('Costo/Prod', digits='Product Price', compute='_compute_unit_cost', store=True)
    quot_cost_component = fields.Float('Costo/Comp', digits='Product Price', compute='_compute_default_cost', store=True, readonly=False)
    lamina_factor = fields.Integer('Cajas/Lamina', default=1)

    @api.depends('product_id', 'quotation_id.currency_rate')
    def _compute_default_cost(self):
        for rec in self:
            rec.quot_cost_component = 0
            if rec.quotation_id and rec.product_id:
                priceinfo = rec.product_id._select_seller(quantity=1, date=fields.Date.context_today(self))
                if priceinfo:
                    rec.quot_cost_component = priceinfo.price / rec.quotation_id.currency_rate
            if rec.quot_cost_component > 0:
                rec.quot_unit_cost = float_round(rec.quot_cost_component / rec.lamina_factor, precision_digits=6)

    @api.depends('quot_cost_component', 'lamina_factor')
    def _compute_unit_cost(self):
        for rec in self:
            rec.quot_unit_cost = float_round(rec.quot_cost_component / rec.lamina_factor, precision_digits=6)

    @api.depends('quotation_id.product_qty', 'lamina_factor')
    def _compute_quot(self):
        for rec in self:
            quot_qty, remain = divmod(rec.quotation_id.product_qty, rec.lamina_factor)
            if remain > 0:
                rec.quot_qty = quot_qty + 1
            else:
                rec.quot_qty = quot_qty
            rec.quot_surface = rec.quot_qty * rec.product_id.surface


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    quotation_id = fields.Many2one('product.quotation.integreat', related='bom_id.quotation_id', store=True)
    quot_currency = fields.Many2one('res.currency', related='quotation_id.currency_id')
    quot_unit_cost = fields.Float('Costo unitario', digits='Product Price', compute='_compute_default_cost', store=True, readonly=False)

    @api.depends('quotation_id.currency_id', 'operation_template_id')
    def _compute_default_cost(self):
        for rec in self:
            rec.quot_unit_cost = 0
            if rec.quotation_id and rec.operation_template_id:
                rec.quot_unit_cost = rec.operation_template_id.cost_price_per_product / rec.quotation_id.currency_rate
