# -*- coding: utf-8 -*-
# greburs by InteGreat

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'
    _order = 'production_id, sequence'

    sequence = fields.Integer('Sequence', default=999, compute='_compute_sequence', store=True, index=True)
    production_sequence = fields.Integer('Production Sequence', default=0)
    product_code = fields.Char(related='product_id.code', string='Producto')
    warehouse_id = fields.Many2one(related='workcenter_id.warehouse_id')
    production_warehouse_id = fields.Many2one(related='production_id.picking_type_id.warehouse_id')
    operation_group = fields.Char(
        'Proceso', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    operation_template_id = fields.Many2one('mrp.routing.wkc.tmpl', 'Operación', check_company=True)
    available_workcenter_ids = fields.Many2many(related='operation_template_id.available_workcenter_ids')
    state_color = fields.Integer(compute='_compute_state_color')
    operation_display_name = fields.Char('Operación', compute='_compute_operation_display_name')
    production_citpa_c_id = fields.Many2one('mrp.production', compute='_compute_process', store=True)
    production_citpa_i_id = fields.Many2one('mrp.production', compute='_compute_process', store=True)
    production_citpa_t_id = fields.Many2one('mrp.production', compute='_compute_process', store=True)
    production_citpa_p_id = fields.Many2one('mrp.production', compute='_compute_process', store=True)
    production_citpa_a_id = fields.Many2one('mrp.production', compute='_compute_process', store=True)
    citpa_c = fields.One2many(related='production_id.citpa_c')
    citpa_i = fields.One2many(related='production_id.citpa_i')
    citpa_t = fields.One2many(related='production_id.citpa_t')
    citpa_p = fields.One2many(related='production_id.citpa_p')
    citpa_a = fields.One2many(related='production_id.citpa_a')
    tinta_name = fields.Char(related="production_id.tinta_name")
    tinta_color = fields.Char(related="production_id.tinta_color")
    qty_possible = fields.Float('Quantity Possible', compute='_compute_qty_possible', digits='Product Unit of Measure', store=True)
    previous_work_order_id = fields.Many2one('mrp.workorder', "Previous Work Order")
    production_reservation_state = fields.Selection(related='production_id.reservation_state')
    workcenter_id = fields.Many2one(
        'mrp.workcenter', 'Work Center', required=True,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)], 'progress': [('readonly', True)]},
        group_expand='_read_group_workcenter_id', check_company=True, domain="[('id', 'in', available_workcenter_ids)]")

    @api.depends('operation_template_id')
    def _compute_sequence(self):
        for wo in self:
            if wo.operation_template_id:
                wo.sequence = wo.operation_template_id.sequence
            else:
                wo.sequence = 0

    # OVERRIDE because we use it in views and is not enought to calculate just at write
    @api.depends('qty_production', 'qty_produced')
    def _compute_qty_remaining(self):
        for wo in self:
            if wo.production_id.product_id:
                wo.qty_remaining = float_round(wo.qty_production - wo.qty_produced,
                                               precision_rounding=wo.production_id.product_uom_id.rounding)
            else:
                wo.qty_remaining = 0

    @api.depends('operation_group')
    def _compute_process(self):
        for wo in self:
            wo.production_citpa_c_id = wo.operation_group == 'C' and wo.production_id or False
            wo.production_citpa_i_id = wo.operation_group == 'I' and wo.production_id or False
            wo.production_citpa_t_id = wo.operation_group == 'T' and wo.production_id or False
            wo.production_citpa_p_id = wo.operation_group == 'P' and wo.production_id or False
            wo.production_citpa_a_id = wo.operation_group == 'A' and wo.production_id or False

    @api.depends('state')
    def _compute_state_color(self):
        for wo in self:
            if wo.state == 'pending':
                wo.state_color = 4
            elif wo.state == 'ready':
                wo.state_color = 10
            elif wo.state == 'progress':
                wo.state_color = 2
            elif wo.state == 'done':
                wo.state_color = 0
            elif wo.state == 'cancel':
                wo.state_color = 1

    def _compute_operation_display_name(self):
        for rec in self:
            rec.operation_display_name = '(%s) %s' % (rec.operation_group, rec.name)

    @api.onchange('operation_template_id')
    def _change_template_id(self):
        for wo in self:
            wo.operation_group = wo.operation_template_id.operation_group
            wo.name = wo.operation_template_id.name
            wo.workcenter_id = wo.operation_template_id.workcenter_id
            wo.sequence = wo.operation_template_id.sequence
            wo.duration_expected = wo.operation_template_id.time_cycle_manual * wo.production_id.product_qty / wo.production_id.unit_factor
            for wc in wo.operation_template_id.available_workcenter_ids:
                if wc == wo.production_id.picking_type_id.warehouse_id:
                    wo.workcenter_id = wc
                    break

    # OVERRIDE completely... no sense to show other info
    def name_get(self):
        res = []
        for wo in self:
            res.append((wo.id, wo.name))
        return res

    # OVERRIDE the logic will be replaced with _compute_qty_possible
    def _action_confirm(self):
        return self._compute_qty_possible()

    @api.depends('qty_production', 'qty_produced', 'previous_work_order_id.qty_produced', 'production_id.state')
    def _compute_qty_possible(self):
        for wo in self:
            wo.qty_possible = 0
            if wo.production_id.state not in ('draft', 'done', 'cancel'):
                # check if planned:
                if not wo.production_id.is_planned:
                    wo.production_id._compute_is_planned()
                if not wo.production_id.is_planned:
                    continue
                if wo.state == 'cancel':
                    continue
                if wo.qty_production == wo.qty_produced:
                    wo.state = 'done'
                    continue
                elif wo.previous_work_order_id:
                    qty_possible = float_round(
                        wo.previous_work_order_id.qty_produced - wo.qty_produced,
                        precision_rounding=wo.production_id.product_uom_id.rounding
                    )
                    if qty_possible > 0:
                        wo.qty_possible = qty_possible
                else:
                    qty_possible = float_round(
                        wo.qty_production - wo.qty_produced, precision_rounding=wo.production_id.product_uom_id.rounding
                    )
                    if qty_possible > 0:
                        wo.qty_possible = qty_possible
                if wo.qty_possible > 0 and wo.production_id.is_planned:
                    if wo.qty_produced == 0:
                        wo.state = 'ready'
                    else:
                        wo.state = 'progress'
                else:
                    wo.state = 'pending'

    def button_partial_done(self):
        for wo in self:
            view_id = self.env.ref('integreat_sale_product_configurator.mrp_workorder_record_qty_wizard_form').id
            return {
                'name': 'Registrar cantidad producida',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.workorder.record.qty.wizard',
                'view_id': view_id,
                'target': 'new',
                'context': {'default_wo_id': wo.id, 'default_qty': wo.qty_possible}
            }

    def button_finish(self):
        for wo in self:
            if wo.env.context.get('skip_wizard'):
                return super().button_finish()
            elif not wo.next_work_order_id:
                view_id = self.env.ref('integreat_sale_product_configurator.mrp_workorder_record_qty_wizard_form').id
                return {
                    'name': 'Registrar cantidad producida',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'res_model': 'mrp.workorder.record.qty.wizard',
                    'view_id': view_id,
                    'target': 'new',
                    'context': {'default_wo_id': wo.id, 'default_qty': wo.qty_possible, 'default_finish': True}
                }
            else:
                wo.qty_produced += wo.qty_possible
                return super().button_finish()

    def record_production(self):
        if not self:
            return True
        self.ensure_one()
        self._check_sn_uniqueness()
        self._check_company()
        if any(x.quality_state == 'none' for x in self.check_ids):
            raise UserError(_('You still need to do the quality checks!'))
        if float_compare(self.qty_producing, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_('Please set the quantity you are currently producing. It should be different from zero.'))
        if self.production_id.product_id.tracking != 'none' and not self.finished_lot_id and self.move_raw_ids:
            raise UserError(_('You should provide a lot/serial number for the final product'))
        # Suggest a finished lot on the next workorder
        if self.next_work_order_id and self.product_tracking != 'none' and not self.next_work_order_id.finished_lot_id:
            self.production_id.lot_producing_id = self.finished_lot_id
            self.next_work_order_id.finished_lot_id = self.finished_lot_id
        self.qty_produced += self.qty_producing
        # One a piece is produced, you can launch the next work order
        self._start_nextworkorder()
        # self.button_finish()
        # if this is the last wo, production will be marked as done
        if not self.next_work_order_id:
            self.production_id.button_mark_done()
        return True
