# -*- coding: utf-8 -*-
# greburs by InteGreat

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.addons.stock.models.stock_rule import ProcurementException
from odoo.osv import expression
from collections import defaultdict


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    type_group = fields.Char('Agrupador manual', required=True, default='X')


class Product(models.Model):
    _inherit = 'product.product'

    variant_route_ids = fields.Many2many('stock.location.route', 'stock_route_product_variant', 'product_variant_id',
        'route_id', 'Routes', domain=[('product_variant_selectable', '=', True)])


class Route(models.Model):
    _inherit = 'stock.location.route'

    product_variant_selectable = fields.Boolean('Applicable on Product Variant', default=False,
        help="When checked, the route will be selectable in the Inventory tab of the Product form.")


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _prepare_mo_vals(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom):
        mo = super()._prepare_mo_vals(product_id, product_qty, product_uom, location_id, name, origin, company_id, values, bom)
        mo['sale_line_id'] = values.get('sale_line_id', False)
        if not values.get('move_dest_ids', False):
            mo['procurement_group_id'] = values.get('group_id', False) and values['group_id'].id or False
        return mo

    # we must override because of this: productions.filtered(lambda p: p.move_raw_ids).action_confirm()
    @api.model
    def _run_manufacture(self, procurements):
        productions_values_by_company = defaultdict(list)
        errors = []
        for procurement, rule in procurements:
            if rule.name == 'Subproducto':
                continue
            bom = self.env['mrp.bom'].search([
                ('product_id', '=', procurement.product_id.id),
                ('picking_type_id', '=', rule.warehouse_id.manu_type_id.id)
            ], limit=1)
            if not bom:
                bom = self.env['mrp.bom'].search([
                    ('product_id', '=', procurement.product_id.id),
                ], limit=1)
            if not bom:
                msg = _('There is no Bill of Material of type manufacture or kit found for the product %s.\n'
                        'Please define a Bill of Material for this product.') % (
                      procurement.product_id.display_name,)
                errors.append((procurement, msg))

            productions_values_by_company[procurement.company_id.id].append(
                rule._prepare_mo_vals(*procurement, bom))

        if errors:
            raise ProcurementException(errors)

        for company_id, productions_values in productions_values_by_company.items():
            # create the MO as SUPERUSER because the current user may not have the rights to do it (mto product launched by a sale for example)
            productions = self.env['mrp.production'].with_user(SUPERUSER_ID).sudo().with_company(company_id). \
                create(productions_values)
            self.env['stock.move'].sudo().create(productions._get_moves_raw_values())
            self.env['stock.move'].sudo().create(productions._get_moves_finished_values())

            productions._create_workorder()
            # productions.filtered(lambda p: p.move_raw_ids).action_confirm()

            for production in productions:
                sale_order = production.sale_line_id and production.sale_order_id
                origin_production = production.move_dest_ids and \
                                    production.move_dest_ids[0].raw_material_production_id or False
                orderpoint = production.orderpoint_id
                if production.workorder_ids:
                    if production.workorder_ids[0].workcenter_id.warehouse_id.manufacture_steps == 'pbm':
                        loc_id = production.workorder_ids[0].workcenter_id.warehouse_id.pbm_loc_id
                    else:
                        loc_id = production.workorder_ids[0].workcenter_id.warehouse_id.lot_stock_id
                    production.location_src_id = production.workorder_ids[0].workcenter_id.warehouse_id.pbm_loc_id
                if sale_order:
                    production.message_post_with_view('mail.message_origin_link',
                                                      values={'self': production, 'origin': sale_order},
                                                      subtype_id=self.env.ref('mail.mt_note').id)
                if orderpoint:
                    production.message_post_with_view('mail.message_origin_link',
                                                      values={'self': production, 'origin': orderpoint},
                                                      subtype_id=self.env.ref('mail.mt_note').id)
                if origin_production:
                    production.message_post_with_view('mail.message_origin_link',
                                                      values={'self': production, 'origin': origin_production},
                                                      subtype_id=self.env.ref('mail.mt_note').id)
        return True


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    sale_order_ids = fields.Many2many(comodel_name="sale.order", string="OV")
    # required additionally to mrp_production_ids, because it is o2m and would change the group_id of production order
    production_ids = fields.Many2many(comodel_name='mrp.production', string="OP")

    @api.model
    def _search_rule(self, route_ids, product_id, warehouse_id, domain):
        """
        Because it is not possible to have different routes on product variants, we introduce the variant_route_ids
        It will be added to the route_ids list => will be applied before the templates route_ids
        """
        if not route_ids:
            route_ids = self.env['stock.location.route']
        if product_id.variant_route_ids:
            route_ids += product_id.variant_route_ids
            if warehouse_id:
                domain = expression.AND(
                    [['|', ('warehouse_id', '=', warehouse_id.id), ('warehouse_id', '=', False)], domain])
            Rule = self.env['stock.rule']
            res = Rule.search(expression.AND([[('route_id', 'in', route_ids.ids)], domain]),
                              order='route_sequence, sequence', limit=1)
            if not res and warehouse_id:
                warehouse_routes = warehouse_id.route_ids
                if warehouse_routes:
                    res = Rule.search(expression.AND([[('route_id', 'in', warehouse_routes.ids)], domain]),
                                      order='route_sequence, sequence', limit=1)
            return res
        return super()._search_rule(route_ids, product_id, warehouse_id, domain)


class Picking(models.Model):
    _inherit = "stock.picking"

    sale_order_ids = fields.Many2many('sale.order', string='OV', compute='_compute_from_group_id', store=True)
    production_ids = fields.Many2many('mrp.production', string='OP', compute='_compute_from_group_id', store=True)
    picking_type_group = fields.Char(related='picking_type_id.type_group')
    production_orig_ids = fields.One2many(comodel_name='mrp.production', compute='_compute_orig_dest_picking_ids')
    picking_orig_ids = fields.One2many(comodel_name='stock.picking', compute='_compute_orig_dest_picking_ids')
    picking_dest_ids = fields.One2many(comodel_name='stock.picking', compute='_compute_orig_dest_picking_ids')
    incoterm = fields.Many2one(related='group_id.sale_id.incoterm', store=True)
    delivery_truck = fields.Char('Detalles transporte')
    delivery_packaging = fields.Char('# Tarimas o Paquetes')

    @api.depends('move_lines.move_orig_ids', 'move_lines.move_dest_ids')
    def _compute_orig_dest_picking_ids(self):
        for pick in self:
            pick.picking_orig_ids = pick.move_lines.move_orig_ids.picking_id
            pick.picking_dest_ids = pick.move_lines.move_dest_ids.picking_id
            pick.production_orig_ids = pick.move_lines.move_orig_ids.production_id

    def action_show_orig_picking(self):
        self.ensure_one()
        action = {
            'name': 'Operación vinculada',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
        }
        if len(self.picking_orig_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.picking_orig_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.picking_orig_ids.ids)],
            })
        return action

    def action_show_dest_picking(self):
        self.ensure_one()
        action = {
            'name': 'Operación vinculada',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
        }
        if len(self.picking_dest_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.picking_dest_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.picking_dest_ids.ids)],
            })
        return action

    def action_show_orig_production(self):
        self.ensure_one()
        action = {
            'name': 'OP vinculada',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
        }
        if len(self.production_orig_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.production_orig_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.production_orig_ids.ids)],
            })
        return action
    
    @api.depends('group_id.sale_order_ids', 'group_id.mrp_production_ids')
    def _compute_from_group_id(self):
        for picking in self:
            picking.sale_order_ids = [(6, 0, picking.group_id.sale_order_ids.ids)]
            picking.production_ids = [(6, 0, picking.group_id.mrp_production_ids.ids + picking.group_id.production_ids.ids)]
