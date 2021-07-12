# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

_STATES = [
    ('00', 'OV Cancelada'),
    ('01', 'OV no suministrada'),
    ('02', 'Produccion no confirmada'),
    ('03', 'OC no creada'),
    ('04', 'OC no confirmada'),
    ('05', 'Esperando Material'),
    ('06', 'Ens. esperando OP Inferior'),
    ('07', 'Material disponible'),
    ('08', 'Produccion no empezada'),
    ('09', 'OP en Proceso'),
    ('10', 'PT Terminado'),
    ('11', 'PT Entregado'),
    ('12', 'OV Facturada'),
    ('99', 'N/A')
]


class SalesFlowWizard(models.TransientModel):
    _name = 'wizard.sale.flow.wizard'
    _description = 'Add new product line'

    report_ids = fields.One2many('wizard.sale.flow.report', 'wiz_id')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    partner_id = fields.Many2one('res.partner', 'Cliente')
    order_id = fields.Many2one('sale.order', 'Orden de Venta')
    product_id = fields.Many2one('product.product', 'Producto')

    def button_create_report(self):
        self.ensure_one()
        self.report_ids = [(5, 0)]
        domain = [('company_id', '=', self.company_id.id)]
        if self.order_id:
            domain += [('order_id', '=', self.order_id.id)]
        else:
            domain += [('invoice_status', '!=', 'invoiced'), ('state', '!=', 'cancel')]
        if self.partner_id:
            domain += [('order_id.partner_id', '=', self.partner_id.id)]
        if self.product_id:
            domain += [('product_id', '=', self.product_id.id)]
        order_lines = self.env['sale.order.line'].search(domain)
        if order_lines:
            report_vals = []
            for line in order_lines:
                lower_ids = []
                if line.production_ids:
                    mos = line.production_ids
                    mos += mos.move_raw_ids.created_production_id
                    mos = mos.filtered(lambda x: x.state not in ('done', 'cancel'))
                    if mos:
                        for mo in mos:
                            components = mo.move_raw_ids.filtered(lambda x: x.product_id.type == 'product')
                            detail_ids = []
                            if components:
                                for component in components:
                                    if component.requested_purreq_line_id:
                                        purreq_id = component.requested_purreq_line_id.id
                                    else:
                                        purreq_id = False
                                    detail_ids.append((0, 0, {
                                        'mo_raw_move': component.id,
                                        'pur_line': purreq_id,
                                    }))
                            else:
                                detail_ids.append((0, 0, {'detail_state': '99'}))
                            lower_ids.append([0, 0, {'level_type': 'production', 'mo_id': mo.id, 'detail_ids': detail_ids}])
                    else:
                        lower_ids.append((0, 0, {'level_state': '99', 'detail_ids': [(0, 0, {'detail_state': '99'})]}))
                elif line.purchase_request_line_ids:
                    for pur in line.purchase_request_line_ids:
                        lower_ids.append((0, 0, {
                            'level_type': 'purchase',
                            'pur_id': pur.id,
                            'detail_ids': [(0, 0, {'pur_line': pur.id})]
                        }))
                else:
                    lower_ids.append((0, 0, {'level_state': '99', 'detail_ids': [(0, 0, {'detail_state': '99'})]}))
                vals = {'sale_line': line.id, 'lower_ids': lower_ids}
                report_vals.append((0, 0, vals))
            self.report_ids = report_vals
        action = {
            'name': 'Reporte Estado Ventas',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'wizard.sale.flow.report.details',
            'domain': [('wiz_id', '=', self.id)],
            'view_id': self.env.ref('integreat_econsa_sales_report.wizard_sales_flow_report_tree').id,
            'search_view_id': self.env.ref('integreat_econsa_sales_report.wizard_sales_flow_search_view').id
        }
        return action


class SalesFlowReport(models.TransientModel):
    _name = 'wizard.sale.flow.report'
    _description = 'Wizard Relation Level 0'
    _order = 'wiz_id, sale_line'

    wiz_id = fields.Many2one('wizard.sale.flow.wizard', index=True)
    sale_line = fields.Many2one('sale.order.line', 'Ln OV', index=True)
    state = fields.Selection(selection=_STATES, string='Estado', compute='_compute_state', store=True)
    lower_ids = fields.One2many('wizard.sale.flow.report.level', 'report_id')

    @api.depends('sale_line', 'lower_ids.level_state')
    def _compute_state(self):
        for line in self:
            replenish_line = self.env['sale.order.line.replenishment'].search([('order_line_id', '=', line.sale_line.id)])
            if line.sale_line.order_id.state == 'cancel':
                line.state = '00'
            elif line.sale_line.invoice_status == 'invoiced':
                line.state = '12'
            elif line.sale_line.qty_delivered >= line.sale_line.product_uom_qty:
                line.state = '11'
            elif (line.sale_line.qty_reserved_delivery + line.sale_line.product_id.free_qty) >= line.sale_line.product_uom_qty:
                line.state = '10'
            elif replenish_line and replenish_line.qty_open_demand > 0:
                line.state = '01'
            elif line.lower_ids:
                line.state = line.lower_ids[0].level_state
            else:
                line.state = '99'


class SalesFlowReportLevel(models.TransientModel):
    _name = 'wizard.sale.flow.report.level'
    _description = 'Wizard Sale Flow Level'
    _order = 'report_id, level_state'

    report_id = fields.Many2one('wizard.sale.flow.report', index=True)
    level_state = fields.Selection(selection=_STATES, string='Estado Prod', compute='_compute_level_state', store=True)
    level_color = fields.Integer('State Color')
    level_type = fields.Selection([('production', 'Production'), ('purchase', 'Purchase')], default='purchase')
    mo_id = fields.Many2one('mrp.production', 'OP')
    pur_id = fields.Many2one('purchase.request.line', 'SC')
    detail_ids = fields.One2many('wizard.sale.flow.report.details', 'level_id')

    @api.depends('mo_id', 'detail_ids.detail_state')
    def _compute_level_state(self):
        for line in self:
            line.level_state = '99'
            if line.mo_id:
                if line.mo_id.state == 'draft':
                    line.level_state = '02'
                    line.level_color = 1
                    continue
                if line.mo_id.state in ('progress', 'to_close'):
                    line.level_state = '09'
                    continue
            if line.detail_ids:
                line.level_state = line.detail_ids[0].detail_state
            if line.level_state == '07':
                picking_ids = self.env['stock.picking'].search([
                    ('group_id', '=', line.mo_id.procurement_group_id.id), ('group_id', '!=', False),
                    ('state', 'not in', ('done', 'cancel'))])
                if not picking_ids:
                    line.level_state = '08'
                    if line.mo_id:
                        line.level_color = 4
            if line.mo_id and line.level_state in ('03', '04', '05', '06'):
                line.level_color = 2
            if line.level_state == '07':
                line.level_color = 3


class SalesFlowReportDetails(models.TransientModel):
    _name = 'wizard.sale.flow.report.details'
    _description = 'Wizard Sale Flow Details'
    _order = 'level_id, detail_state'

    level_id = fields.Many2one('wizard.sale.flow.report.level')
    report_id = fields.Many2one(related='level_id.report_id', store=True)
    wiz_id = fields.Many2one(related='report_id.wiz_id', store=True)
    detail_state = fields.Selection(selection=_STATES, string='Estado Compra', compute='_compute_detail_state', store=True)
    level_state = fields.Selection(related='level_id.level_state', store=True)
    state = fields.Selection(related='report_id.state', store=True)
    sale_line = fields.Many2one('sale.order.line', compute='_compute_upper_data', store=True)
    sale_id = fields.Many2one('sale.order', compute='_compute_upper_data', string='OV', store=True)
    sale_create_uid = fields.Many2one('res.users', compute='_compute_upper_data', string='OV creado por', store=True)
    product_id = fields.Many2one('product.product', compute='_compute_upper_data', string='Producto', store=True)
    sale_date = fields.Datetime(compute='_compute_upper_data', string='Fecha req.', store=True)
    product_qty = fields.Float(compute='_compute_upper_data', string='Ctd(P)', store=True)
    product_qty_reserved = fields.Float(compute='_compute_upper_data', string='Reservado(P)', store=True)
    product_qty_delivered = fields.Float(compute='_compute_upper_data', string='Entregado(P)', store=True)
    product_qty_invoiced = fields.Float(compute='_compute_upper_data', string='Facturado(P)', store=True)
    product_qty_free = fields.Float(compute='_compute_upper_data', string='Disponible(P)', store=True)
    mo_id = fields.Many2one(related='level_id.mo_id', store=True)
    level_color = fields.Integer(related='level_id.level_color')
    mo_date = fields.Datetime(compute='_compute_upper_data', string='Fecha fin.')
    mo_raw_move = fields.Many2one('stock.move', string='Comp Raw Move')
    comp_id = fields.Many2one(related='mo_raw_move.product_id', string='Componente', store=True)
    comp_qty = fields.Float(related='mo_raw_move.product_uom_qty', string='Ctd(C)')
    comp_qty_reserved = fields.Float(compute='_compute_data', string='Asignado(C)')
    comp_qty_free = fields.Float(related='mo_raw_move.product_id.free_qty', string='Disponible(C)')
    picking_ids = fields.One2many('stock.picking', compute='_compute_data', string='Sel#')
    pur_line = fields.Many2one('purchase.request.line', string='SC')
    purchased_qty = fields.Float(related='pur_line.purchased_qty', string='Ctd OC')
    po_ids = fields.One2many('purchase.order', compute='_compute_data', string='OC')
    po_date = fields.Datetime(string='Fecha OC')
    detail_color = fields.Integer('Detail Color')

    @api.depends('level_id', 'level_id.report_id')
    def _compute_upper_data(self):
        self.report_id.sale_line._compute_qty_delivered()
        for line in self:
            line.sale_line = line.report_id.sale_line
            line.sale_id = line.report_id.sale_line.order_id
            line.sale_create_uid = line.sale_id.create_uid
            line.product_id = line.report_id.sale_line.product_id
            line.sale_date = line.report_id.sale_line.order_id.commitment_date
            line.product_qty = line.report_id.sale_line.product_uom_qty
            line.product_qty_reserved = line.report_id.sale_line.qty_reserved_delivery
            line.product_qty_delivered = line.report_id.sale_line.qty_reserved_delivery
            line.product_qty_invoiced = line.report_id.sale_line.qty_invoiced
            line.product_qty_free = line.report_id.sale_line.product_id.free_qty
            if line.level_id:
                line.mo_date = line.level_id.mo_id.date_planned_finished
            else:
                line.mo_date = False

    @api.depends('mo_raw_move', 'pur_line')
    def _compute_data(self):
        for line in self:
            line.picking_ids = line.mo_raw_move.move_orig_ids.picking_id \
                if line.mo_raw_move and line.mo_raw_move.move_orig_ids else False
            if line.mo_raw_move:
                if line.mo_raw_move.move_orig_ids:
                    line.comp_qty_reserved = \
                            sum(line.mo_raw_move.move_orig_ids.mapped('reserved_availability')) + \
                            sum(line.mo_raw_move.move_orig_ids.mapped('quantity_done'))
                else:
                    line.comp_qty_reserved = line.mo_raw_move.reserved_availability
            else:
                line.comp_qty_reserved = 0
            line.po_ids = line.pur_line.purchase_lines.order_id \
                if line.pur_line and line.pur_line.purchase_lines else []
            line.po_date = line.po_ids[0].date_order \
                if line.po_ids else False

    @api.depends('pur_line', 'comp_qty_reserved', 'comp_qty_free')
    def _compute_detail_state(self):
        for line in self:
            if line.pur_line:
                if not line.pur_line.purchase_lines:
                    line.detail_state = '03'
                    line.detail_color = 1
                elif line.pur_line.purchase_state not in ('purchase', 'done'):
                    line.detail_state = '04'
                    line.detail_color = 2
                elif line.pur_line.pending_qty_to_receive > 0:
                    line.detail_state = '05'
                elif line.pur_line.pending_qty_to_receive <= 0:
                    line.detail_state = '07'
            if line.mo_raw_move:
                if line.mo_raw_move.created_production_id \
                        and line.mo_raw_move.created_production_id.state not in ('done', 'cancel'):
                    line.detail_state = '06'
                if line.mo_raw_move.product_uom_qty <= line.comp_qty_reserved + line.comp_qty_free:
                    line.detail_state = '07'
                if not line.detail_state and not line.pur_line:
                    line.detail_state = '03'
            if not line.pur_line and not line.mo_raw_move:
                line.detail_state = '99'
