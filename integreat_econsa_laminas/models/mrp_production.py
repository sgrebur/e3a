# -*- coding: utf-8 -*-
# sgrebur InteGreat

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_round


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    @api.constrains('product_id')
    def _check_lamina(self):
        for line in self:
            if line.bom_id.product_id.is_lamina_required and line.bom_id.type == 'normal':
                if line.product_id.categ_id == self.env.ref('integreat_sale_product_configurator.lamina'):
                    raise ValidationError('Las láminas deben seleccionarse durante el proceso de producción,\n'
                                          'por lo que no está permitido agregarlas a la lista de materiales.')


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    unit_factor = fields.Float('Pzs/Herr', related='bom_id.product_qty', store=True)
    is_lamina_required = fields.Boolean(related='product_id.product_tmpl_id.is_lamina_required', store=True)
    lamina_open_qty = fields.Float('Selección faltante', digits='Product Unit of Measure',
        compute='_compute_lamina_open_qty', readonly=True)
    count_lamina = fields.Integer('Count laminas', compute='_compute_lamina_open_qty')
    purchase_request_ids = fields.Many2many('purchase.request', string='Purchase Requests',
        compute='_compute_purchase_requests')
    purchase_request_count = fields.Integer('Compras', compute='_compute_purchase_requests')

    @api.depends('procurement_group_id')
    def _compute_purchase_requests(self):
        for mo in self:
            mo.purchase_request_ids = self.env['purchase.request'].search([
                ('group_id', '=', mo.procurement_group_id.id), ('group_id', '!=', False)
            ])
            mo.purchase_request_count = len(mo.purchase_request_ids.line_ids)

    def action_view_purchase_requests(self):
        request_line_ids = self.purchase_request_ids.line_ids.ids
        return {
            'name': _("Solicitudes de compra generadas por %s", self.name),
            'res_model': 'purchase.request.line',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', request_line_ids)],
            'view_mode': 'tree,form',
        }

    def button_purreq_wizard(self):
        self.action_assign()
        wiz_lines = []
        for move in self.move_raw_ids:
            wiz_lines.append((0, 0, {'move_id': move.id}))
        wiz = self.env['mrp.purchase.request.wizard'].create({'production_id': self.id, 'line_ids': wiz_lines})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Solicitar compra additional por Orden %s' % self.name,
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'mrp.purchase.request.wizard',
            'res_id': wiz.id
        }

    @api.model
    def create(self, values):
        if values.get('product_id', False):
            product = self.env['product.product'].browse(values.get('product_id'))
            if product.is_lamina_required:
                values['is_lamina_required'] = product.is_lamina_required
        return super(MrpProduction, self).create(values)

    @api.depends('move_raw_ids.product_uom_qty')
    def _compute_lamina_open_qty(self):
        for mo in self:
            if mo.is_lamina_required and mo.state == 'draft':
                lamina_id = self.env.ref('integreat_sale_product_configurator.lamina').id
                laminas = mo.move_raw_ids.filtered(lambda m: m.product_id.categ_id.id == lamina_id)
                assigned = sum(laminas.mapped('products_possible_qty')) or 0
                mo.lamina_open_qty = mo.product_qty - assigned
                mo.count_lamina = len(laminas)
            else:
                mo.lamina_open_qty = 0
                mo.count_lamina = 0

    def action_select_lamina(self):
        vals = {
            'production_id': self.id,
            'product_id': self.product_id.id,
            'location_id': False,
            'pza_por_herr': self.unit_factor,
            'qty': self.lamina_open_qty,
            'calibre': self.product_id.spec_calibre,
            'papel': self.product_id.spec_papel,
            'flauta': self.product_id.spec_flauta,
            'recub': self.product_id.spec_recub,
            'ancho': self.product_id.spec_ancho_lamina or self.product_id.spec_ancho,
            'largo': self.product_id.spec_largo_lamina or self.product_id.spec_largo
        }
        wiz = self.env['wizard.lamina.selection'].create(vals)
        wiz.action_compute_lines()
        return wiz.lamina_wizard_action(wiz.id)

    def action_confirm(self):
        self._compute_next_workorders_and_warehouse()
        lamina_categ_id = self.env.ref('integreat_sale_product_configurator.lamina').id        
        for production in self:
            if production.suaje and production.suaje.state == 'blocked':
                self.env.user.notify_danger(message='El suaje está bloqueado. ¡Verifique con su departamento técnico!')
            prod_origin_qty = production.product_qty
            all_new_production = []
            if not production.workorder_ids:
                raise UserError('No hay ningún proceso de trabajo definido.\n'
                                'Defínalos y actualice la lista de procesos en el BOM del producto.')
            if production.lamina_open_qty > 0:
                raise UserError('¡La cantidad de láminas asignadas no cubre la cantidad de producción!')
            elif production.lamina_open_qty < 0:
                raise UserError('La cantidad de la orden de producción es menor\n'
                                'que la cantidad posible de las láminas asignadas.\n'
                                '¡sin corrección no es posible confirmar!')
            laminas = production.move_raw_ids.filtered(lambda m: m.product_id.categ_id.id == lamina_categ_id)
            if len(laminas) > 1:
                remaining_qty = production.product_qty
                counter = 0
                for lamina in laminas:
                    counter = counter + 1
                    if counter == 1:
                        continue
                    remaining_qty -= lamina.products_possible_qty

                    new_production = production.copy(default={'origin': production.origin})
                    all_new_production.append({
                        'production': new_production,
                        'new_qty': lamina.products_possible_qty,
                        'lamina_id': lamina.product_id.id,
                        'lamina_qty': lamina.product_uom_qty,
                    })
                all_new_production.append({
                    'production': production,
                    'new_qty': laminas[0].products_possible_qty,
                    'lamina_id': laminas[0].product_id.id,
                    'lamina_qty': laminas[0].product_uom_qty,
                })
            else:
                all_new_production.append({'production': production})

            for mo in all_new_production:
                # change production qty (with wizard from mrp module), remove other laminas, create PurReq for lamina
                prod = mo.get('production', False)
                if not prod:  # should not happen...
                    continue
                if mo.get('new_qty', False):
                    new_qty = mo.get('new_qty')
                    self.change_prod_qty(prod, new_qty)
                    lamina_id = mo.get('lamina_id')
                    moves_to_delete = (prod.move_raw_ids | prod.move_finished_ids).filtered(
                        lambda m:
                            m.product_id.categ_id.id == lamina_categ_id
                            and m.product_id.id != lamina_id
                    )
                    moves_to_delete.unlink()
                    # change back lamina qty:
                    lamina_move = prod.move_raw_ids.filtered(lambda m: m.product_id.id == lamina_id)
                    lamina_qty = mo.get('lamina_qty', False)
                    lamina_move.product_uom_qty = lamina_qty
                    if prod != production:
                        message = "Esta orden es el resultado de una división.<br/>La orden de origen es: "
                        message += "<a target='_blank' href='%s'>%s</a>" % (
                            '/web#id=%s&view_type=form&model=mrp.production' % (production.id), production.name,
                        )
                        message += "<br/>La cantidad original fue: " + str(production.product_qty) + " pzs"
                        prod.message_post(body=message, message_type='notification')
                    else:
                        message = "Esta orden se ha dividido. La cantidad original fue: " + str(prod_origin_qty) + " pzs"
                        message += "<br/>Las otras órdenes creadas son:"
                        for p in all_new_production:
                            other_prod = p.get('production', False)
                            if other_prod != production:
                                message += "<ul><li><a target='_blank' href='%s'>%s;</a></li><ul/>" % (
                                    '/web#id=%s&view_type=form&model=mrp.production' % (other_prod.id), other_prod.name,
                                )
                        prod.message_post(body=message, message_type='notification')

                # this is the original part of action_confirm (from mrp\...\mrp_production.py)
                if prod.bom_id:
                    prod.consumption = prod.bom_id.consumption
                if not prod.move_raw_ids:
                    raise UserError(_("Add some materials to consume before marking this MO as to do."))
                # In case of Serial number tracking, force the UoM to the UoM of product
                if prod.product_tracking == 'serial' and prod.product_uom_id != prod.product_id.uom_id:
                    prod.write({
                        'product_qty': prod.product_uom_id._compute_quantity(prod.product_qty,
                                                                                   prod.product_id.uom_id),
                        'product_uom_id': prod.product_id.uom_id
                    })
                    for move_finish in prod.move_finished_ids.filtered(
                            lambda m: m.product_id == prod.product_id):
                        move_finish.write({
                            'product_uom_qty': move_finish.product_uom._compute_quantity(move_finish.product_uom_qty,
                                                                                         move_finish.product_id.uom_id),
                            'product_uom': move_finish.product_id.uom_id
                        })
                prod.move_raw_ids._adjust_procure_method()
                (prod.move_raw_ids | prod.move_finished_ids)._action_confirm()
                prod.workorder_ids._action_confirm()
                # run scheduler for moves forecasted to not have enough in stock
                prod.move_raw_ids._trigger_scheduler()

                # own addition: assign + printed: avoid merge pickings + create lamina PurReq
                try:
                    prod.picking_ids.action_assign()
                except:
                    pass
                prod.picking_ids.write({'printed': True})
                prod.action_assign()
                # do it for all components automatically
                for raw in prod.move_raw_ids:
                    required = 0
                    # when component pickings
                    if raw.move_orig_ids and raw.product_id.type == 'product' and not raw.route_ids and not raw.move_orig_ids.production_id:
                        required = sum(raw.move_orig_ids.mapped('product_uom_qty')) \
                                   - sum(raw.move_orig_ids.mapped('quantity_done')) \
                                   - sum(raw.move_orig_ids.mapped('reserved_availability'))
                    # when 1-step production
                    elif not raw.move_orig_ids and raw.product_id.type == 'product' and not raw.route_ids:
                        required = raw.product_uom_qty - raw.quantity_done - raw.reserved_availability
                    if required > 0 and prod.purchase_request_ids:
                        required -= sum(prod.purchase_request_ids.line_ids.
                                        filtered(lambda l: l.product_id == raw.product_id).mapped('product_qty'))
                        free = raw.product_id.with_context(warehouse=prod.location_src_id.get_warehouse().id).free_qty
                        if required > free:
                            qty = required - free
                            prod._run_lamina_procurement(raw.product_id, qty, [raw])
        return True

    # # Componets PICKING must be processed before production launch
    # def button_plan(self):
    #
    #     component_picking_types = self.env['stock.warehouse'].search([]).pbm_type_id.mapped('id')
    #     for mo in self:
    #         picking_ids = self.env['stock.picking'].search([
    #             ('group_id', '=', mo.procurement_group_id.id), ('group_id', '!=', False),
    #             ('picking_type_id', 'in', component_picking_types)
    #         ])
    #         if picking_ids:
    #             raw_picking_done = any(p.state == 'done' for p in picking_ids)
    #             if raw_picking_done is False:
    #                 raise UserError('Antes de programar y lanzar la producción,\n'
    #                                 'la transferencia de los componentes debe ser procesada.')
    
    def _run_lamina_procurement(self, product, qty, request_move_ids):
        procurements = []
        location_dest_id = self.picking_type_id.warehouse_id.wh_input_stock_loc_id
        values = {
            'group_id': self.procurement_group_id,
            'date_planned': self.date_planned_start,
            'origin': self.name,
            'request_move_ids': request_move_ids
        }
        procurements.append(
            self.env['procurement.group'].Procurement(
                product, qty, product.uom_id, location_dest_id, self.name, self.name, self.company_id, values
            )
        )
        if procurements:
            self.env['procurement.group'].run(procurements)

    # override: remove lamina issues!
    def _get_consumption_issues(self):
        issues = super()._get_consumption_issues()
        lamina_id = self.env.ref('integreat_sale_product_configurator.lamina').id
        new_issues = []
        for issue in issues:
            if issue[1].categ_id.id != lamina_id:
                new_issues.append(issue)
        return new_issues

    # was not called from the wizard... copy from mrp\wizard\change_production_qty.py
    def _update_finished_moves(self, production, new_qty, old_qty):
        """ Update finished product and its byproducts. This method only update
        the finished moves not done or cancel and just increase or decrease
        their quantity according the unit_ratio. It does not use the BoM, BoM
        modification during production would not be taken into consideration.
        """
        modification = {}
        for move in production.move_finished_ids:
            if move.state in ('done', 'cancel'):
                continue
            qty = (new_qty - old_qty) * move.unit_factor
            modification[move] = (move.product_uom_qty + qty, move.product_uom_qty)
            move.write({'product_uom_qty': move.product_uom_qty + qty})
        return modification

    # was not called from the wizard... copy from mrp\wizard\change_production_qty.py
    def change_prod_qty(self, production, new_qty):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        produced = sum(production.move_finished_ids.filtered(lambda m: m.product_id == production.product_id).mapped('quantity_done'))
        if new_qty < produced:
            format_qty = '%.{precision}f'.format(precision=precision)
            raise UserError(_(
                "You have already processed %(quantity)s. Please input a quantity higher than %(minimum)s ",
                quantity=format_qty % produced,
                minimum=format_qty % produced
            ))
        old_production_qty = production.product_qty
        new_production_qty = new_qty
        done_moves = production.move_finished_ids.filtered(lambda x: x.state == 'done' and x.product_id == production.product_id)
        qty_produced = production.product_id.uom_id._compute_quantity(sum(done_moves.mapped('product_qty')), production.product_uom_id)

        factor = (new_production_qty - qty_produced) / (old_production_qty - qty_produced)
        production._update_raw_moves(factor)
        self._update_finished_moves(production, new_production_qty - qty_produced, old_production_qty - qty_produced)
        production.write({'product_qty': new_production_qty})

        for wo in production.workorder_ids:
            operation = wo.operation_id
            wo.duration_expected = wo._get_duration_expected(ratio=new_production_qty / old_production_qty)
            quantity = wo.qty_production - wo.qty_produced
            if production.product_id.tracking == 'serial':
                quantity = 1.0 if not float_is_zero(quantity, precision_digits=precision) else 0.0
            else:
                quantity = quantity if (quantity > 0 and not float_is_zero(quantity, precision_digits=precision)) else 0
            wo._update_qty_producing(quantity)
            if wo.qty_produced < wo.qty_production and wo.state == 'done':
                wo.state = 'progress'
            if wo.qty_produced == wo.qty_production and wo.state == 'progress':
                wo.state = 'done'
                if wo.next_work_order_id.state == 'pending':
                    wo.next_work_order_id.state = 'ready'
            # assign moves; last operation receive all unassigned moves
            # TODO: following could be put in a function as it is similar as code in _workorders_create
            # TODO: only needed when creating new moves
            moves_raw = production.move_raw_ids.filtered(lambda move: move.operation_id == operation and move.state not in ('done', 'cancel'))
            if wo == production.workorder_ids[-1]:
                moves_raw |= production.move_raw_ids.filtered(lambda move: not move.operation_id)
            moves_finished = production.move_finished_ids.filtered(lambda move: move.operation_id == operation) #TODO: code does nothing, unless maybe by_products?
            moves_raw.mapped('move_line_ids').write({'workorder_id': wo.id})
            (moves_finished + moves_raw).write({'workorder_id': wo.id})
        return {}

    # OVERRIDE when producing qty > mo qty: components consumed won't be increased
    # def _set_qty_producing(self):
    #     super(MrpProduction, self)._set_qty_producing()
    #     for move in self.move_raw_ids:
    #         if move.quantity_done > move.product_qty:
    #             move.move_line_ids.filtered(lambda ml: ml.state not in ('done', 'cancel')).qty_done = 0
    #             move.move_line_ids = move._set_quantity_done_prepare_vals(move.product_qty)


class StockMove(models.Model):
    _inherit = 'stock.move'

    products_possible_qty = fields.Float('P/C', digits='Product Unit of Measure',
        compute='compute_products_per_component', readonly=True, store=True)

    # different unit_factor based on component (different laminas have different size!)
    @api.onchange('product_uom_qty', 'product_id')
    def onchange_compute_unit_factor(self):
        if self.raw_material_production_id and \
                self.product_id.categ_id.id == self.env.ref('integreat_sale_product_configurator.lamina').id:
            self._compute_unit_factor()
            self.compute_products_per_component()

    @api.depends('product_uom_qty', 'unit_factor')
    def compute_products_per_component(self):
        for move in self:
            move.products_possible_qty = 0
            if move.raw_material_production_id and move.state != 'done' and move.product_uom_qty > 0:
                move.products_possible_qty = float_round(move.product_uom_qty / move.unit_factor, precision_digits=0)

    @api.depends('product_uom_qty',
                 'raw_material_production_id', 'raw_material_production_id.product_qty',
                 'raw_material_production_id.qty_produced',
                 'production_id', 'production_id.product_qty', 'production_id.qty_produced')
    def _compute_unit_factor(self):
        super(StockMove, self)._compute_unit_factor()
        for move in self:
            if move.raw_material_production_id.product_id \
                    and move.raw_material_production_id.product_id.is_lamina_required \
                    and move.product_id.categ_id.id == self.env.ref('integreat_sale_product_configurator.lamina').id:
                production_ancho = max(move.raw_material_production_id.product_id.spec_ancho_lamina,
                                   move.raw_material_production_id.product_id.spec_ancho)
                production_largo = max(move.raw_material_production_id.product_id.spec_largo_lamina,
                                   move.raw_material_production_id.product_id.spec_largo)
                qty_ancho = move.product_id.spec_ancho // production_ancho
                qty_largo = move.product_id.spec_largo // production_largo
                if qty_ancho < 1 or qty_largo < 1:
                    raise UserError(_('¡El tamaño de la lámina %s es menor a lo requerido!', move.product_id.display_name))
                move.unit_factor = 1 / move.raw_material_production_id.unit_factor / (qty_ancho * qty_largo)

    @api.depends('raw_material_production_id.qty_producing', 'product_uom_qty')
    def _compute_should_consume_qty(self):
        super(StockMove, self)._compute_should_consume_qty()
        for move in self:
            if move.raw_material_production_id.product_id and \
                    move.product_id.categ_id.id == self.env.ref('integreat_sale_product_configurator.lamina').id:
                if move.should_consume_qty > move.product_qty:
                    move.should_consume_qty = move.product_qty
