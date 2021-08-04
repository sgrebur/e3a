# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    suaje = fields.Many2one(related='bom_id.suaje', store=True)
    suaje_transfer_state = fields.Char('Suaje OP status')
    grabado = fields.Many2one(related='bom_id.grabado', store=True)
    grabado_transfer_state = fields.Char('Grabado OP status')
    recub = fields.Char('Recubrimiento', related="product_id.spec_recub")
    recub_lamina = fields.Char('Recubrimiento lamina', compute='_compute_components_specifics', store=True)
    citpa_c = fields.One2many('mrp.workorder', 'production_citpa_c_id', string='C')
    citpa_i = fields.One2many('mrp.workorder', 'production_citpa_i_id', string='I')
    citpa_t = fields.One2many('mrp.workorder', 'production_citpa_t_id', string='T')
    citpa_p = fields.One2many('mrp.workorder', 'production_citpa_p_id', string='P')
    citpa_a = fields.One2many('mrp.workorder', 'production_citpa_a_id', string='A')
    tinta_name = fields.Char('Tinta', compute='_compute_tinta', store=True)
    tinta_color = fields.Char('#', compute='_compute_tinta', store=True)
    product_qty_conf = product_qty = fields.Float('Cantidad original', digits='Product Unit of Measure', readonly=True)

    # from whatever reason move_finished_ids are sometimes missing (deleted by users???)
    def button_mark_done(self):
        for mo in self:
            mo._onchange_move_finished()
            mo._set_qty_producing()
            mo.action_assign()
            move_lines_zero = mo.move_raw_ids.move_line_ids.filtered(lambda x: x.location_id.usage == 'view')
            # when manuf 1 step & negative stock allowed & pbm_loc a view location, we set it to the pbm
            if move_lines_zero:
                move_lines_zero.location_id = mo.picking_type_id.warehouse_id.pbm_loc_id
        return super().button_mark_done()

    def button_plan(self):
        self.action_assign()
        if not self._context.get('with_no_stock', False):
            no_reservation = self.filtered(lambda x: x.reservation_state != 'assigned')
            if no_reservation:
                wizard = self.env['mrp.production.plan.wizard'].create({
                    'productions': [(6, 0, self.ids)]
                })
                return {
                    'name': 'Confirmar lanzamiento de producción',
                    'type': 'ir.actions.act_window',
                    'view_mode': 'form',
                    'target': 'new',
                    'res_model': 'mrp.production.plan.wizard',
                    'res_id': wizard.id
                }
        res = super().button_plan()
        for mo in self:
            mo.workorder_ids._action_confirm()
        return res

    @api.depends('move_raw_ids')
    def _compute_tinta(self):
        tinta_categ = self.env.ref('data.prd_cat_Tinta').id
        for p in self:
            tintas = p.move_raw_ids.filtered(lambda m: m.product_id.categ_id.id == tinta_categ)
            if tintas:
                p.tinta_name = tintas[0].product_id.default_code
                p.tinta_color = tintas[0].product_id.product_template_attribute_value_ids[1].html_color
            else:
                p.tinta_name = False
                p.tinta_color = False

    # def action_confirm(self):
        # FIRST WE HAVE TO RUN THE BELOW 2 METHODS, BUT SINCE IT IS OVERRIDEN
        # IN THE MODULE integreat_econsa_laminas IT IS DONE THERE

    # called at confirm (than wo's must be blocked for editing!)
    def _compute_next_workorders_and_warehouse(self):
        for mo in self:
            mo.write_previous_next_order()
            for wo in mo.workorder_ids:
                if wo.workcenter_id.warehouse_id and wo.workcenter_id.warehouse_id != mo.picking_type_id.warehouse_id:
                    if not wo.previous_work_order_id:
                        mo.location_src_id = wo.workcenter_id.warehouse_id.pbm_loc_id
                        for move in mo.move_raw_ids:
                            if not move.operation_id or move.operation_id == wo.operation_id:
                                move.location_id = wo.workcenter_id.warehouse_id.pbm_loc_id
                                move.warehouse_id = wo.workcenter_id.warehouse_id
                    else:
                        for move in mo.move_raw_ids:
                            if move.operation_id == wo.operation_id:
                                move.location_id = wo.workcenter_id.warehouse_id.pbm_loc_id
                                move.warehouse_id = wo.workcenter_id.warehouse_id

    # called at confirm (than wo's must be blocked for editing!)
    def write_previous_next_order(self):
        workorders = self.workorder_ids.sorted()
        last = len(workorders) - 1
        if last > 0:
            workorders[0].previous_work_order_id = False
            workorders[0].next_work_order_id = workorders[1]
            workorders[last].next_work_order_id = False
            workorders[last].previous_work_order_id = workorders[last - 1]
        if last > 1:
            for n in range(1, last):
                workorders[n].previous_work_order_id = workorders[n - 1]
                workorders[n].next_work_order_id = workorders[n + 1]

    def _get_ready_to_produce_state(self):
        res = super(MrpProduction, self)._get_ready_to_produce_state()
        self.ensure_one()
        if all(move.state == 'assigned' for move in self.move_raw_ids):
            return 'assigned'
        return res

    @api.depends('move_raw_ids.product_id.spec_recub')
    def _compute_components_specifics(self):
        for production in self:
            recub_lamina = []
            for comp in production.move_raw_ids:
                if comp.product_id.spec_recub:
                    recub_lamina.append(comp.product_id.spec_recub)
            if len(recub_lamina) == 1:
                production.recub_lamina = recub_lamina[0]
            elif len(recub_lamina) > 1:
                production.recub_lamina = 'Multiple'
            else:
                production.recub_lamina = 'Faltante'

    #OVERRIDE
    def _create_workorder(self):
        for production in self:
            if not production.bom_id:
                continue
            workorders_values = []
            product_qty = production.product_uom_id._compute_quantity(production.product_qty,
                                                                      production.bom_id.product_uom_id)
            exploded_boms, dummy = production.bom_id.explode(production.product_id,
                                                             product_qty / production.bom_id.product_qty,
                                                             picking_type=production.bom_id.picking_type_id)
            for bom, bom_data in exploded_boms:
                # If the operations of the parent BoM and phantom BoM are the same, don't recreate work orders.
                if not (bom.operation_ids and (not bom_data['parent_line']
                        or bom_data['parent_line'].bom_id.operation_ids != bom.operation_ids)):
                    continue
                for operation in bom.operation_ids:
                    workorders_values += [{
                        'sequence': operation.sequence,
                        'operation_group': operation.operation_group,
                        'operation_template_id': operation.operation_template_id.id,
                        'name': operation.name,
                        'production_id': production.id,
                        'workcenter_id': operation.workcenter_id.id,
                        'product_uom_id': production.product_uom_id.id,
                        'operation_id': operation.id,
                        'state': 'pending',
                        'consumption': production.consumption,
                    }]
            production.workorder_ids = [(5, 0)] + [(0, 0, value) for value in workorders_values]
            for workorder in production.workorder_ids:
                workorder.duration_expected = workorder._get_duration_expected()

    def write(self, vals):
        res = super(MrpProduction, self).write(vals)
        for p in self:
            if 'date_finished' in vals:
                p.workorder_ids.filtered(lambda w: w.state != 'done').write({'state': 'done'})
            if not p.date_deadline and p.date_planned_finished:
                p.date_deadline = p.date_planned_finished
            if vals.get('state', False) and vals.get('state') == 'confirmed':
                p.product_qty_conf = p.product_qty
        return res

    def button_transfer_suaje(self):
        return {
            'name': 'Trasferencia Suaje por Orden de Producción ' + self.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.equipment.transfer.wizard',
            'view_id': self.env.ref('integreat_sale_product_configurator.mrp_equipment_transfer_wizard').id,
            'target': 'new',
            'context': {
                'default_production_transfer': True,
                'default_production_id': self.id,
                'default_equipment_id': self.suaje.id,
            }
        }

    def button_return_suaje(self):
        for production in self:
            production.suaje.write({
                'dest_location_id': production.suaje.default_location_id.id,
                'production_id': False
            })
            production.suaje_transfer_state = False

    def button_transfer_grabado(self):
        return {
            'name': 'Trasferencia Grabado por Orden de Producción ' + self.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.equipment.transfer.wizard',
            'view_id': self.env.ref('integreat_sale_product_configurator.mrp_equipment_transfer_wizard').id,
            'target': 'new',
            'context': {
                'default_production_transfer': True,
                'default_production_id': self.id,
                'default_equipment_id': self.grabado.id,
            }
        }

    def button_return_grabado(self):
        for production in self:
            production.grabado.write({
                'dest_location_id': production.grabado.default_location_id.id,
                'production_id': False,
            })
            production.grabado_transfer_state = False

    # must be overriden, just because the generated backorder.workorder_ids are not sorted
    # as addition removed to set producing qty
    def _generate_backorder_productions(self, close_mo=True):
        backorders = self.env['mrp.production']
        for production in self:
            if production.backorder_sequence == 0:  # Activate backorder naming
                production.backorder_sequence = 1
            backorder_mo = production.copy(default=production._get_backorder_mo_vals())
            if close_mo:
                production.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write({
                    'raw_material_production_id': backorder_mo.id,
                })
                production.move_finished_ids.filtered(lambda m: m.state not in ('done', 'cancel')).write({
                    'production_id': backorder_mo.id,
                })
            else:
                new_moves_vals = []
                for move in production.move_raw_ids | production.move_finished_ids:
                    if not move.additional:
                        qty_to_split = move.product_uom_qty - move.unit_factor * production.qty_producing
                        qty_to_split = move.product_uom._compute_quantity(qty_to_split, move.product_id.uom_id, rounding_method='HALF-UP')
                        move_vals = move._split(qty_to_split)
                        if not move_vals:
                            continue
                        if move.raw_material_production_id:
                            move_vals[0]['raw_material_production_id'] = backorder_mo.id
                        else:
                            move_vals[0]['production_id'] = backorder_mo.id
                        new_moves_vals.append(move_vals[0])
                new_moves = self.env['stock.move'].create(new_moves_vals)
            backorders |= backorder_mo
            for old_wo, wo in zip(
                    production.workorder_ids.sorted(),
                    backorder_mo.workorder_ids.sorted()
            ):
                wo.qty_produced = max(old_wo.qty_produced - old_wo.qty_producing, 0)
                # if wo.product_tracking == 'serial':
                #     wo.qty_producing = 1
                # else:
                #     wo.qty_producing = wo.qty_remaining
                # if wo.qty_producing == 0:
                #     wo.action_cancel()

            production.name = self._get_name_backorder(production.name, production.backorder_sequence)

            # We need to adapt `duration_expected` on both the original workorders and their
            # backordered workorders. To do that, we use the original `duration_expected` and the
            # ratio of the quantity really produced and the quantity to produce.
            ratio = production.qty_producing / production.product_qty
            for workorder in production.workorder_ids:
                workorder.duration_expected = workorder.duration_expected * ratio
            for workorder in backorder_mo.workorder_ids:
                workorder.duration_expected = workorder.duration_expected * (1 - ratio)

        # As we have split the moves before validating them, we need to 'remove' the excess reservation
        if not close_mo:
            self.move_raw_ids.filtered(lambda m: not m.additional)._do_unreserve()
            self.move_raw_ids.filtered(lambda m: not m.additional)._action_assign()

        # It can happen that all components have been consumed already in the original OP (lamina 1 pzs = many products)
        for backorder in backorders:
            if not backorder.move_raw_ids:
                backorder.is_lamina_required = False
                dummy_prod = self.env['product.product'].search([('default_code', '=', 'X-XXXX')], limit=1)
                dummy_prod = self._get_move_raw_values(dummy_prod, 1, dummy_prod.uom_id)
                backorder.move_raw_ids = [(0, 0, dummy_prod)]

        # Confirm only productions with remaining components
        backorders.filtered(lambda mo: mo.move_raw_ids).action_confirm()
        backorders.filtered(lambda mo: mo.move_raw_ids).action_assign()

        # Remove the serial move line without reserved quantity. Post inventory will assigned all the non done moves
        # So those move lines are duplicated.
        backorders.move_raw_ids.move_line_ids.filtered(lambda ml: ml.product_id.tracking == 'serial' and ml.product_qty == 0).unlink()
        backorders.move_raw_ids._recompute_state()

        return backorders

    def _get_move_raw_values(self, product_id, product_uom_qty, product_uom, operation_id=False, bom_line=False):
        data = super(MrpProduction, self)._get_move_raw_values(product_id, product_uom_qty, product_uom, operation_id, bom_line)
        if bom_line and bom_line.route_id:
            data['route_ids'] = [(4, bom_line.route_id.id)]
        return data
