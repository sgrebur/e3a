# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    warehouse_id = fields.Many2one('stock.warehouse', string="Planta")
    wo_running = fields.Boolean('Running Workorders', compute="_compute_running_workorders", store=True)

    @api.depends('order_ids.state')
    def _compute_running_workorders(self):
        for wkc in self:
            wkc.wo_running = len(wkc.order_ids.filtered(lambda o: o.state in ('ready', 'progress')))

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '[%s] %s' % (rec.code, rec.name)))
        return res


class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    operation_group = fields.Selection([
        ('C', 'C'),
        ('I', 'I'),
        ('T', 'T'),
        ('P', 'P'),
        ('A', 'A')
    ], string="Proceso", required=True)
    operation_template_id = fields.Many2one('mrp.routing.workcenter.template')
    available_workcenters_from_template = fields.Many2many(related='operation_template_id.available_workcenter_ids')
    time_cycle_manual = fields.Float(default=0.0166666666666667)

    @api.onchange('operation_template_id')
    def _change_template_id(self):
        for rec in self:
            if rec.operation_template_id:
                rec.sequence = rec.operation_template_id.sequence
                rec.operation_group = rec.operation_template_id.operation_group
                rec.name = rec.operation_template_id.name
                rec.workcenter_id = rec.operation_template_id.workcenter_id
                

class MrpRoutingWorkcenterTemplate(models.Model):
    _name = 'mrp.routing.workcenter.template'
    _description = 'Operations Template'
    _inherit = 'mrp.routing.workcenter'

    available_workcenter_ids = fields.Many2many(comodel_name='mrp.workcenter',
        relation='routing_template_workcenter_m2m', column1='template_id', column2='wc_id',
        string="Centros de producción disponibles")
    cost_price_per_product = fields.Float('Costo/Producto', digits='Product Price', default=0.0)

    @api.constrains('name', 'bom_id', 'operation_group')
    def _check_constraint(self):
        for rec in self:
            if rec.bom_id:
                return {
                    'warning': {
                        'title': 'Atención',
                        'message': 'En la plantilla de operación modelo\n no se permite seleccionar ninguna lista de materiales.'
                    }
                }

    _sql_constraints = [
        ('name_unique', 'unique(name, operation_group, warehouse_id)',
         'La combinación del proceso y el nombre de la operación debe ser única por planta.'),
    ]

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, '(%s) %s' % (rec.operation_group, rec.name)))
        return res
