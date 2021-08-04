# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.tools import float_round
from odoo.exceptions import ValidationError


class LaminaSelection(models.TransientModel):
    _name = 'wizard.lamina.selection'
    _description = 'Lamina Selection'

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, 'Buscador de Lámina (%s)' % rec.id))
        return res

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        # recub_search = self.env['product.attribute.value'].\
        #    search([('attribute_id.name', '=', 'Recubrimiento'), ('name', '=', 'Sin. recub')], limit=1)
        res.update({
        #    'recub_search': recub_search.id,
            'origen': 'NAL'
        })
        return res

    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda self: self.env.company)
    update = fields.Boolean('Update')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order')
    warehouse_id = fields.Many2one('stock.warehouse', compute='_compute_warehouse_id', store=True, domain="[('company_id', '=', company_id)]")
    line_ids = fields.One2many('wizard.lamina.selection.line', 'wizard_id')
    product_id = fields.Many2one('product.product', string='Producto Terminado')
    currency_id = fields.Many2one('res.currency', related='product_id.currency_id')
    location_id = fields.Many2one('stock.location')
    papel = fields.Char('Papel', compute='_compute_spec_values', store=True, readonly=False)
    flauta = fields.Char('Flauta', compute='_compute_spec_values', store=True, readonly=False)
    recub = fields.Char('Recubrimiento', compute='_compute_spec_values', store=True, readonly=False)
    calibre = fields.Char('Calibre', compute='_compute_spec_values', store=True, readonly=False)
    calibre_search = fields.Many2one('product.attribute.value', 'Calibre ', domain="[('attribute_id.name', '=', 'Calibre')]")
    papel_search = fields.Many2one('product.attribute.value', 'Papel ', domain="[('attribute_id.name', '=', 'Papel')]")
    flauta_search = fields.Many2one('product.attribute.value', 'Flauta ', domain="[('attribute_id.name', '=', 'Flauta')]")
    recub_search = fields.Many2one('product.attribute.value', 'Recubrimiento ', domain="[('attribute_id.name', '=', 'Recubrimiento')]")
    ancho = fields.Integer('Ancho necesario', default=1)
    largo = fields.Integer('Largo necesario', default=1)
    origen = fields.Selection([('NAL', 'NAL'), ('IND', 'IND'), ('HAZ', 'HAZ')], string='Origen')
    pza_por_herr = fields.Float('Pza/Lamina', default=1.0, required=True, digits='Unit of Measure')
    qty = fields.Float('Requeridas', default=1.0, digits='Product Unit of Measure')
    total_qty = fields.Float('Planificadas', compute='_compute_sum', digits='Product Unit of Measure')
    total_qty_gauge = fields.Float('Seleccion', compute='_compute_sum')
    total_cost = fields.Monetary('Costo', currency_field='currency_id', compute='_compute_sum')
    total_waste = fields.Monetary('Desperdicio', currency_field='currency_id', compute='_compute_sum')
    total_util = fields.Float('Utilizacion')
    select_single = fields.Boolean('Multiple laminas?')

    @api.depends('production_id')
    def _compute_warehouse_id(self):
        for wiz in self:
            if wiz.production_id:
                wiz.warehouse_id = wiz.production_id.location_src_id.get_warehouse()
            else:
                wiz.warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)

    @api.depends('line_ids.product_id', 'line_ids.qty_selected')
    def _compute_sum(self):
        for rec in self:
            total_cost = 0.0
            total_waste = 0.0
            total_qty = 0.0
            for line in self.line_ids:
                total_cost += line.line_cost
                total_waste += line.line_waste
                total_qty += line.qty_cajas
            rec.total_cost = total_cost
            rec.total_waste = total_waste
            rec.total_qty = total_qty
            rec.total_qty_gauge = total_qty

    # @api.onchange('product_id')
    # def _compute_spec_values_and_load(self):
    #     for wiz in self:
    #         if wiz.product_id:
    #             wiz.write({'product_id': wiz.product_id})
    #             wiz.action_compute_lines()

    @api.depends('product_id', 'calibre_search', 'papel_search', 'flauta_search', 'recub_search')
    def _compute_spec_values(self):
        for wiz in self:
            if wiz.product_id:
                wiz.calibre = wiz.product_id.spec_calibre or False
                wiz.papel = wiz.product_id.spec_papel or False
                wiz.flauta = wiz.product_id.spec_flauta or False
                wiz.recub = wiz.product_id.spec_recub or False
                wiz.origen = wiz.product_id.spec_origen or False
                wiz.ancho = wiz.product_id.spec_ancho_lamina or wiz.product_id.spec_ancho or 0
                wiz.largo = wiz.product_id.spec_largo_lamina or wiz.product_id.spec_largo or 0
            if wiz.calibre_search:
                wiz.calibre = wiz.calibre_search.name
            if wiz.papel_search:
                wiz.papel = wiz.papel_search.name
            if wiz.flauta_search:
                wiz.flauta = wiz.flauta_search.name
            if wiz.recub_search:
                wiz.recub = wiz.recub_search.name

    def action_compute_lines(self):
        self.ensure_one()
        self.line_ids.unlink()
        domain = [
            ('categ_id', '=', self.env.ref('integreat_sale_product_configurator.lamina').id),
            ('spec_papel', '=', self.papel),
            ('spec_flauta', '=', self.flauta),
            ('spec_recub', 'in', ['Sin recub.', self.recub]),
            ('spec_origen', '=', self.origen),
            ('spec_ancho', '>=', self.ancho),
            ('spec_largo', '>=', self.largo),
        ]
        if self.calibre_search:
            domain = domain + [('spec_calibre', 'in', [self.calibre_search.name])]
        if self.origen:
            domain += [('spec_origen', '=', self.origen)]
        components = self.env['product.product'].search(domain)
        if self.warehouse_id:
            this_wh = self.warehouse_id.id
            other_whs = self.env['stock.warehouse'].search([
                ('company_id', '=', self.company_id.id),
                ('id', '!=', this_wh)
            ], limit=1) # LIMIT1 !!! If there are 2 Whs for the company...
        vals_list = []
        max_lines = 0

        # FREE from this Planta
        for comp in components:
            if self.warehouse_id:
                comp = comp.with_context(warehouse=this_wh)
            if not comp.free_qty > 0.0:
                continue
            max_lines += 1
            vals = {
                'wizard_id': self.id,
                'line_group': '1',
                'product_id': comp.id,
                }
            if self.warehouse_id:
                vals['warehouse_id'] = this_wh
            vals_list.append(vals)
            if max_lines == 30:
                break

        # free from OTHER Planta
        if len(vals_list) < 30 and self.warehouse_id:
            max_lines = len(vals_list)
            for comp in components:
                comp = comp.with_context(warehouse=other_whs.id)
                if not comp.free_qty > 0.0:
                    continue
                max_lines += 1
                vals = {
                    'wizard_id': self.id,
                    'line_group': '1',
                    'product_id': comp.id,
                    'warehouse_id': other_whs.id
                    }
                vals_list.append(vals)
                if max_lines == 30:
                    break

        # all other w/o stock
        if len(vals_list) < 30:
            max_lines = len(vals_list)
            for comp in components:
                if comp.free_qty > 0.0:
                    continue
                max_lines += 1
                vals = {
                    'wizard_id': self.id,
                    'line_group': '2',
                    'product_id': comp.id,
                    }
                if self.warehouse_id:
                    vals['warehouse_id'] = this_wh
                vals_list.append(vals)
                if max_lines == 30:
                    break

        domain = [
            ('categ_id', '=', self.env.ref('integreat_sale_product_configurator.lamina').id),
            ('spec_calibre', '=', self.calibre),
            ('spec_papel', '=', self.papel),
            ('spec_flauta', '=', self.flauta),
            ('spec_recub', '=', self.recub),
            ('spec_ancho', '=', self.ancho),
            ('spec_largo', '=', self.largo)
        ]
        if self.origen:
            domain += [('spec_origen', '=', self.origen)]
        new_component = self.env['product.product'].search(domain, limit=1)
        if new_component:
            if self.production_id:
                is_already = list(filter(lambda l: l['product_id'] == new_component.id and l['warehouse_id'] == this_wh, vals_list))
            else:
                is_already = list(
                    filter(lambda l: l['product_id'] == new_component.id, vals_list))
            if not is_already:
                vals = {
                    'wizard_id': self.id,
                    'line_group':  '0',
                    'product_id': new_component.id,
                }
                if self.production_id:
                    vals['warehouse_id'] = this_wh
                vals_list.append(vals)
            else:
                is_already[0]['line_group'] = '0'
        lines = []
        for rec in vals_list:
            lines.append([0, 0, rec])
        self.line_ids = lines

    def action_reload(self):
        for wiz in self:
            wiz.action_compute_lines()
            if not self._context.get('fullscreen', False):
                return self.lamina_wizard_action(self.id)

    def action_add_to_mo(self):
        new_raw_ids = []
        for line in self.line_ids:
            if line.select:
                existing_move = self.env['stock.move'].search([
                    ('raw_material_production_id', '=', self.production_id.id),
                    ('product_id', '=', line.product_id.id)
                ], limit=1)
                if existing_move:
                    existing_move.product_uom_qty += line.qty_selected
                    continue
                new_raw = self.production_id._get_move_raw_values(
                    line.product_id,
                    line.qty_selected,
                    line.product_id.uom_id
                )
                new_raw['group_id'] = self.production_id.procurement_group_id.id
                new_raw['origin'] = self.production_id.name
                if line.warehouse_id != self.warehouse_id:
                    if line.qty_selected > line.free_qty:
                        raise ValidationError(
                            'No se permite seleccionar de otra planta una cantidad superior a la cantidad Libre.'
                        )
                    ico_route = self.env['stock.location.route'].search([
                        ('rule_ids.location_id', '=', self.production_id.location_src_id.id),
                        ('rule_ids.location_src_id', '=', line.warehouse_id.lot_stock_id.id)
                    ], limit=1)
                    if ico_route:
                        new_raw['route_ids'] = [(4, ico_route.id)]
                new_raw_ids.append(new_raw)
        self.env['stock.move'].with_context(overwrite=True).create(new_raw_ids)
        self.unlink()
        return True

    def get_new_raw_id(self, line):
        vals = {
            'date': self.production_id.date_planned_start,
            'date_deadline': self.production_id.date_deadline,
            'location_id': self.production_id.location_src_id.id,
            'location_dest_id': self.production_id.production_location_id.id,
            'state': 'draft',
            'raw_material_production_id': self.production_id.id,
            'picking_type_id': self.production_id.picking_type_id.id,
            'company_id': self.production_id.company_id.id,
            'product_id': line.product_id.id,
            'group_id': self.production_id.procurement_group_id.id,
            'reference': self.production_id.name
        }
        return vals

    def lamina_wizard_action(self, wiz_id):
        view_id = self.env.ref('integreat_econsa_laminas.wizard_lamina_selection_form').id
        action = {
            'name': 'Selección láminas',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'wizard.lamina.selection',
            'view_id': view_id,
            'res_id': wiz_id
        }
        if not self._context.get('fullscreen', False):
            action['target'] = 'new'
        return action

    def add_lamina(self):
        return {
            'name': 'Seleccionar lámina',
            'type': 'ir.actions.act_window',
            'view_id': self.env.ref('integreat_econsa_laminas.wizard_lamina_selection_product_select').id,
            'view_mode': 'form',
            'res_model': 'wizard.lamina.selection.product.select',
            'target': 'new',
            'context': {'default_wiz_id': self.id}
        }


class LaminaSelectionAvailability(models.TransientModel):
    _name = 'wizard.lamina.selection.line'
    _description = 'Lamina Availability'
    _order = 'wizard_id, line_group, product_id'

    wizard_id = fields.Many2one('wizard.lamina.selection', ondelete='set null')
    line_group = fields.Selection([
        ('0', 'Definida'),
        ('1', 'Con disponibilidad'),
        ('2', 'Sin disponibilidad')
    ], string='Grouping', default='2')
    select = fields.Boolean('Selection Checkbox')
    location = fields.Many2one('stock.location')
    warehouse_id = fields.Many2one('stock.warehouse')
    product_id = fields.Many2one('product.product', string='Componente')
    prod_papel = fields.Char(related="wizard_id.papel")
    prod_flauta = fields.Char(related="wizard_id.flauta")
    prod_recub = fields.Char(related="wizard_id.recub")
    prod_ancho = fields.Integer(related="wizard_id.ancho")
    prod_largo = fields.Integer(related="wizard_id.largo")
    calibre = fields.Char(related='product_id.spec_calibre')
    ancho = fields.Integer(related='product_id.spec_ancho')
    largo = fields.Integer(related='product_id.spec_largo')
    standard_price = fields.Float(related='product_id.standard_price')
    currency_id = fields.Many2one('res.currency', related='product_id.currency_id')
    qty_available = fields.Float(related='product_id.qty_available')
    free_qty = fields.Float('Libre', compute='_compute_free_qty')
    incoming_qty = fields.Float(related='product_id.incoming_qty')
    outgoing_qty = fields.Float(related='product_id.outgoing_qty')
    unit_cost = fields.Monetary('Costo/Caja', compute='_compute_values', currency_field='currency_id')
    unit_waste = fields.Monetary('Desp/Caja', compute='_compute_values', currency_field='currency_id')
    util = fields.Float('Utilizacion', compute='_compute_values', digits=(9, 2))
    qty_per_component = fields.Float('Cajas/Lamina', digits="Unit Of Measure", compute='_compute_values', store=True)
    qty_possible = fields.Float('Cajas Posibles', digits="Product Unit Of Measure", compute='_compute_values', store=True)
    qty_required = fields.Float('Required Laminas', digits="Product Unit Of Measure", compute='_compute_values', store=True)
    qty_selected = fields.Float('Selección', default=0, digits='Product Unit of Measure')
    qty_cajas = fields.Float('Cajas Total', default=0, digits='Product Unit of Measure')
    line_cost = fields.Monetary('Costo', currency_field='currency_id')
    line_waste = fields.Monetary('Desperdicio', currency_field='currency_id')
    sob_ancho = fields.Integer('SobA')
    sob_largo = fields.Integer('SobL')
    seller_id = fields.Many2one('product.supplierinfo', domain=[('product_id', '=', product_id)])
    partner_id = fields.Many2one('res.partner', related='seller_id.name')
    seller_price = fields.Float(related='seller_id.price')
    seller_moq = fields.Float(related='seller_id.min_qty')
    marca1 = fields.Char(related='product_id.spec_marca1')
    marca2 = fields.Char(related='product_id.spec_marca2')
    marca3 = fields.Char(related='product_id.spec_marca3')

    @api.depends('product_id', 'warehouse_id')
    def _compute_free_qty(self):
        for line in self:
            if line.warehouse_id:
                line.free_qty = line.product_id.with_context(warehouse=line.warehouse_id.id).free_qty
            else:
                line.free_qty = line.product_id.free_qty

    @api.depends('product_id')
    def _compute_values(self):
        for line in self:
            if line.product_id and line.wizard_id:
                qty_ancho, sob_ancho = divmod(line.ancho, line.wizard_id.ancho)
                qty_largo, sob_largo = divmod(line.largo, line.wizard_id.largo)
                line.sob_ancho = sob_ancho
                line.sob_largo = sob_largo
                line.util = ((line.ancho - line.sob_ancho) * (line.largo - line.sob_largo)) / (line.ancho * line.largo)
                # line.util_display = '{:.1%}'.format(line.util)
                line.qty_per_component = qty_ancho * qty_largo * line.wizard_id.pza_por_herr
                try:
                    line.qty_required = float_round((line.wizard_id.qty - line.wizard_id.total_qty) / line.qty_per_component,
                                                    precision_digits=0, rounding_method='UP')
                except ZeroDivisionError:
                    line.qty_required = 0
                line.qty_possible = line.qty_per_component * line.free_qty
                if line.standard_price > 0 and line.qty_per_component > 0:
                    line.unit_cost = line.standard_price / line.qty_per_component
                else:
                    line.unit_cost = 0
                line.unit_waste = line.unit_cost - (line.unit_cost * line.util)
                line.seller_id = line.product_id._select_seller(quantity=line.qty_required, date=fields.Date.today())
            else:
                line.sob_ancho, line.sob_largo, line.util, line.qty_per_component, line.qty_required,\
                    line.qty_possible, line.unit_cost, line.unit_waste, line.seller_id = \
                    0, 0, 0, 0, 0, 0, 0, 0, False

    @api.onchange('qty_selected')
    def onchange_qty_selected(self):
        try:
            self.qty_required = float_round((self.wizard_id.qty - self.wizard_id.total_qty
                + (self._origin.qty_selected * self.qty_per_component)) /
                self.qty_per_component, precision_digits=0, rounding_method='UP')
        except ZeroDivisionError:
            self.qty_required = 0
        if self.warehouse_id != self.wizard_id.warehouse_id and self.qty_selected > self.free_qty:
            self.qty_selected = self.free_qty
            return {
                'warning': {
                    'title': 'Attention!',
                    'message': 'No se permite seleccionar una cantidad superior a la Libre\n'
                               'cuando se transfiere de la otra planta.'
                }
            }
        if self.qty_selected > self.qty_required:
            self.qty_selected = self.qty_required
            return {
                'warning': {
                    'title': 'Attention!',
                    'message': 'No se permite seleccionar una cantidad superior a la requerida.\n'
                               'Si desea aumentar la cantidad producida, hágalo en la orden de producción.'
                }
            }
        self.select = False

    def select_line(self):
        vals = {}
        if self.qty_selected == 0.0:
            if self.wizard_id.select_single:
                self.wizard_id.line_ids.write({
                    'qty_selected': 0,
                    'line_cost': 0,
                    'line_waste': 0,
                    'qty_cajas': 0,
                    'select': False
                })
                self.qty_selected = self.qty_required
            else:
                if self.line_group == '1':
                    self.qty_selected = min(self.free_qty, self.qty_required)
                else:
                    self.qty_selected = self.qty_required
        vals = {
            'qty_selected': self.qty_selected,
            'line_cost': self.qty_selected * self.unit_cost,
            'line_waste': self.qty_selected * self.unit_waste,
            'qty_cajas': self.qty_selected * self.qty_per_component,
            'select': True
        }
        self.write(vals)

        if self.wizard_id.production_id and self.wizard_id.total_qty > self.wizard_id.qty:
            mo_id = self.wizard_id.production_id.id
            mo_qty = self.wizard_id.production_id.product_qty
            open_qty = self.wizard_id.qty
            total_qty = self.wizard_id.total_qty
            new_qty = mo_qty - open_qty + total_qty
            return {
                'name': 'Update MO Quantity',
                'type': 'ir.actions.act_window',
                'view_id': self.env.ref('mrp.view_change_production_qty_wizard').id,
                'view_mode': 'form',
                'res_model': 'change.production.qty',
                'target': 'new',
                'context': {
                    'default_mo_id': mo_id,
                    'default_product_qty': new_qty,
                    'default_lamina_selector': self.wizard_id.id
                }
            }
        elif not self._context.get('fullscreen', False):
            return self.wizard_id.lamina_wizard_action(self.wizard_id.id)

    def deselect_line(self):
        vals = {
            'qty_selected': 0,
            'line_cost': 0,
            'line_waste': 0,
            'qty_cajas': 0,
            'select': False
        }
        self.write(vals)
        return self.wizard_id.lamina_wizard_action(self.wizard_id.id)


class LaminaSelectionLineGroup(models.TransientModel):
    _name = 'wizard.lamina.selection.group'
    _description = 'Lamina Availability Grouping'

    name = fields.Char('Name')


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    def _set_product_qty(self):
        """ The meaning of product_qty field changed lately and is now a functional field computing the quantity
        in the default product UoM. This code has been added to raise an error if a write is made given a value
        for `product_qty`, where the same write should set the `product_uom_qty` field instead, in order to
        detect errors. """
        # sgrebur: did not find any solution. production qty updated with wizard, than this action
        if self._context.get('overwrite', False):
            for move in self:
                move.product_qty = move.product_uom_qty
            return
        return super(StockMove, self)._set_product_qty()
