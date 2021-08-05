# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpWorkordorRecordQtyWizard(models.TransientModel):
    _name = 'mrp.workorder.record.qty.wizard'
    _description = 'Mrp Workordor Record Qty Wizard'

    wo_id = fields.Many2one('mrp.workorder', string='Operación')
    mo_id = fields.Many2one(related='wo_id.production_id', string='OP')
    qty = fields.Float('Cantidad producida', digits='Product Unit of Measure')
    mark_done = fields.Boolean('Mark Done', compute='_compute_mark_done')
    to_backorder = fields.Boolean('To Backorder', compute='_compute_mark_done')
    finish = fields.Boolean('Finish Button')
    qty_info = fields.Float('Cantidad info', digits='Product Unit of Measure', compute='_compute_mark_done')

    @api.onchange('qty')
    def _compute_mark_done(self):
        self.mark_done = False
        self.to_backorder = False
        self.qty_info = self.qty
        if not self.wo_id.next_work_order_id:
            if self.qty == self.wo_id.qty_possible:
                self.mark_done = True
            if self.qty < self.wo_id.qty_production:
                self.to_backorder = True

    def record_workorder_qty(self):
        wo = self.wo_id
        mo = self.mo_id
        if self.qty == 0:
            return
        # if self.qty > wo.qty_possible:
        #     self.qty = wo.qty_possible
        #     raise UserError('No es posible producir una cantidad mayor que la cantidad de producción\n'
        #                     'o la cantidad ya producida en la orden de trabajo anterior.')
        if not self.wo_id.next_work_order_id:
            wo.qty_produced += self.qty
            if mo.qty_producing < wo.qty_produced:
                mo.qty_producing = wo.qty_produced
                mo._set_qty_producing()
            # from whatever reason move_finished_ids are sometimes missing (deleted by users???)
            if self.to_backorder:
                self.unlink()
                mo.with_context(skip_consumption=True, skip_backorder=True, mo_ids_to_backorder=mo.ids, skip_wizard=True).button_mark_done()
            else:
                self.unlink()
                mo.with_context(skip_consumption=True).button_mark_done()
            for prod in mo.procurement_group_id.mrp_production_ids.filtered(lambda p: p.state not in ('done', 'cancel')):
                prod.button_plan()
            return True
        else:
            wo.qty_produced += self.qty
            if mo.qty_producing < wo.qty_produced:
                mo.qty_producing = wo.qty_produced
                mo._set_qty_producing()
                mo.action_assign()
            self.unlink()
            if wo.qty_production > wo.qty_produced:
                if wo.next_work_order_id.state == 'pending':
                    wo.next_work_order_id.write({'state': 'ready'})
                return wo.button_pending()
            else:
                return wo.button_finish()
