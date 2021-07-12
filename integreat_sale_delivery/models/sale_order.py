# -*- coding: utf-8 -*-
# greburs by InteGreat

from odoo import api, fields, models, _
from datetime import timedelta


class ResPartner(models.Model):
    _inherit = 'res.partner'

    transport_days = fields.Float('Transport days', digits=(12, 2),
                                  help='Transport days: dispatch will be calculated based on this')


class SaleOrder(models.Model):
    _inherit = "sale.order"

    date_order = fields.Datetime(string='Order Date',
        required=True, readonly=True, index=True, copy=False, default=fields.Datetime.now,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)]},
        help="Order issue date at customer.\n..changed by InteGreat.")
    commitment_date = fields.Datetime(string='Dispatch Date', compute='_compute_date_dispatch', store=True,
        copy=False, readonly=True, help="This is the dispatch date promised to the customer.",
        states={'draft': [('readonly', True)], 'sent': [('readonly', True)], 'sale': [('readonly', True)]})
    date_delivery = fields.Datetime('Delivery Date', copy=False, readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)], 'sale': [('readonly', False)]},
        help="This is the calculated dispatch date.")
    delivery_status = fields.Selection([
        ('open', 'Open'),
        ('waiting', 'Waiting Picking'),
        ('noavail', 'Check Availability'),
        ('ready', 'Ready to Deliver'),
        ('partial', 'Partially Delivered'),
        ('done', 'Delivered'),
        ('notrelevant', 'Not relevant'),
    ], compute='_compute_delivery_status', string='Delivery Status', store=True, readonly=True, copy=False, index=True)
    incoterm = fields.Many2one(default=lambda self: self.env.company.incoterm_id)

    @api.onchange('partner_shipping_id')
    def _compute_incoterm(self):
        for order in self:
            if order.partner_shipping_id and order.partner_shipping_id.incoterm:
                order.incoterm = order.partner_shipping_id.incoterm

    @api.depends('order_line.line_delivery_status')
    def _compute_delivery_status(self):
        sort_map = {
            'notrelevant': 7,
            'done': 6,
            'open': 5,
            'ready': 4,
            'noavail': 3,
            'waiting': 2,
            'partial': 1,
        }
        for order in self:
            order.delivery_status = 'notrelevant'
            if not order.state == 'cancel':
                lines_sorted = order.mapped('order_line').sorted(key=lambda m: sort_map.get(m.line_delivery_status, 0))
                if lines_sorted:
                    if lines_sorted[0].line_delivery_status:
                        order.delivery_status = lines_sorted[0].line_delivery_status

    @api.depends('date_delivery', 'date_order')
    def _compute_date_dispatch(self):
        for order in self:
            if order.date_delivery:
                dated = fields.Datetime.from_string(order.date_delivery) - timedelta(
                    days=order.partner_shipping_id.transport_days or 0.0)
            else:
                dated = fields.Datetime.now()
            order.commitment_date = fields.Datetime.to_string(max(dated, fields.Datetime.now()))

    # create delivery action will be available whenever order qty is not covered by delivery pickings
    def button_action_deliver(self):
        self.order_line._action_launch_stock_rule()

    # this is called from button action_confirm: OVERRIDE date_order will be calculated and not Datetime.now()
    def _prepare_confirmation_values(self):
        return {'state': 'sale'}


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    line_delivery_status = fields.Selection([
        ('open', 'Open'),
        ('waiting', 'Waiting Picking'),
        ('noavail', 'Check Availability'),
        ('ready', 'Ready to Deliver'),
        ('partial', 'Partially Delivered'),
        ('done', 'Delivered'),
        ('notrelevant', 'Not relevant'),
    ], compute='_compute_line_delivery_status', string='Delivery Status', store=True, readonly=True, copy=False,
        index=True)
    qty_in_delivery = fields.Float('Quantity in Delivery', copy=False, compute='_compute_qty_delivered',
        compute_sudo=True, digits='Product Unit of Measure', default=0.0)
    qty_reserved_delivery = fields.Float('Reserved Delivery', copy=False, compute='_compute_qty_delivered',
        compute_sudo=True, digits='Product Unit of Measure', default=0.0)

    # OVERRIDE from sale_stock
    @api.depends('move_ids.state', 'move_ids.scrapped', 'move_ids.product_uom',
                 'move_ids.product_uom_qty', 'move_ids.reserved_availability')
    def _compute_qty_delivered(self):
        super(SaleOrderLine, self)._compute_qty_delivered()

        for line in self:  # TODO: maybe one day, this should be done in SQL for performance sake
            qty_delivered = 0.0
            qty_in_delivery = 0.0
            qty_reserved_delivery = 0.0
            if line.qty_delivered_method == 'stock_move':
                outgoing_moves, incoming_moves = line._get_outgoing_incoming_moves()
                for move in outgoing_moves:
                    qty_reserved_delivery += move.product_uom._compute_quantity(
                            move.reserved_availability, line.product_uom, rounding_method='HALF-UP')
                    if move.state != 'done':
                        qty_in_delivery += move.product_uom._compute_quantity(
                            move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                    else:
                        qty_delivered += move.product_uom._compute_quantity(
                            move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                for move in incoming_moves:
                    qty_reserved_delivery -= move.product_uom._compute_quantity(
                            move.reserved_availability, line.product_uom, rounding_method='HALF-UP')
                    if move.state != 'done':
                        qty_in_delivery -= move.product_uom._compute_quantity(
                            move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
                    else:
                        qty_delivered -= move.product_uom._compute_quantity(
                            move.product_uom_qty, line.product_uom, rounding_method='HALF-UP')
            line.qty_delivered = qty_delivered
            line.qty_in_delivery = qty_in_delivery
            line.qty_reserved_delivery = qty_reserved_delivery

    @api.depends('move_ids.state', 'qty_delivered_method', 'product_uom_qty')
    def _compute_line_delivery_status(self):
        sort_map = {
            'done': 6,
            'assigned': 5,
            'partially_available': 4,
            'confirmed': 3,
            'waiting': 2,
            'draft': 1
        }
        for line in self:
            status = 'notrelevant'
            delivery_qty = line.qty_delivered + line.qty_in_delivery
            if line.state != 'cancel' and line.product_uom_qty > 0.0 and line.qty_delivered_method == 'stock_move':
                if line.move_ids:
                    if 0 < delivery_qty < line.product_uom_qty:
                        status = 'partial'
                    elif delivery_qty == 0:
                        status = 'open'
                    else:
                        moves = line.move_ids.filtered(lambda m: (m.state != 'cancel')).sorted(
                            key=lambda x: sort_map.get(x.state, 0))
                        if moves:
                            # get just most relevant status
                            if moves[0].state in ('draft', 'waiting'):
                                status = 'waiting'
                            elif moves[0].state in ('partially_available', 'confirmed'):
                                status = 'noavail'
                            elif moves[0].state == 'assigned':
                                status = 'ready'
                            elif moves[0].state == 'done':
                                status = 'done'
            line.line_delivery_status = status
