# -*- coding: utf-8 -*-
# greburs by InteGreat

from odoo import api, fields, models, SUPERUSER_ID, _


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    sale_order_id = fields.Many2one(related='sale_line_id.order_id', string="OV", store=True, readonly=True)
    sale_line_id = fields.Many2one('sale.order.line', string="OV Ln", index=True)
    sale_partner_name = fields.Char(string='Cliente', compute='_compute_partner_name')
    is_printed = fields.Boolean(string='Printed')

    @api.depends('sale_line_id')
    def _compute_partner_name(self):
        for mo in self:
            partner = mo.sale_line_id.order_id.partner_id.commercial_partner_id
            if partner.partner_code:
                mo.sale_partner_name = partner.partner_code
            elif partner:
                mo.sale_partner_name = partner.name[0:7] + "..."
            else:
                mo.sale_partner_name = ''

    # + orders from sale replenishment
    @api.depends('procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id', 'sale_order_id')
    def _compute_sale_order_count(self):
        super(MrpProduction, self)._compute_sale_order_count()
        for production in self:
                production.sale_order_count += len(production.sale_order_id)

    # override: + sale orders added to the logic
    def action_view_sale_orders(self):
        self.ensure_one()
        sale_order_ids = self.procurement_group_id.mrp_production_ids.move_dest_ids.group_id.sale_id.ids \
            + [self.sale_order_id.id]
        action = {
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
        }
        if len(sale_order_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': sale_order_ids[0],
            })
        else:
            action.update({
                'name': _("Sources Sale Orders of %s", self.name),
                'domain': [('id', 'in', sale_order_ids)],
                'view_mode': 'tree,form',
            })
        return action

    @api.onchange('bom_id', 'product_id', 'product_qty', 'product_uom_id')
    def _onchange_move_raw(self):
        if not self.bom_id and not self._origin.product_id:
            return
        # # Clear move raws if we are changing the product. In case of creation (self._origin is empty),
        # # we need to avoid keeping incorrect lines, so clearing is necessary too.
        if self.product_id != self._origin.product_id:
            # self.move_raw_ids = [(5,)]
            # keep also in this case manual entries
            [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]
        if self.bom_id and self.product_qty > 0:
            # keep manual entries
            list_move_raw = [(4, move.id) for move in self.move_raw_ids.filtered(lambda m: not m.bom_line_id)]
            moves_raw_values = self._get_moves_raw_values()
            move_raw_dict = {move.bom_line_id.id: move for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)}
            for move_raw_values in moves_raw_values:
                if move_raw_values['bom_line_id'] in move_raw_dict:
                    # update existing entries
                    list_move_raw += [(1, move_raw_dict[move_raw_values['bom_line_id']].id, move_raw_values)]
                else:
                    # add new entries
                    list_move_raw += [(0, 0, move_raw_values)]
            self.move_raw_ids = list_move_raw
        else:
            self.move_raw_ids = [(2, move.id) for move in self.move_raw_ids.filtered(lambda m: m.bom_line_id)]


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    sale_order_id = fields.Many2one(string='O.Venta',
        related='production_id.sale_order_id', store=True)
    sale_partner_name = fields.Char(string='Cliente',
        related='production_id.sale_partner_name', store=True)
    launch_status = fields.Char(compute='_compute_launch_status', store=True)

    @api.depends('state', 'previous_work_order_id', 'production_id.is_printed')
    def _compute_launch_status(self):
        for wo in self:
            wo.launch_status = False
            if wo.state == 'ready' and not wo.previous_work_order_id:
                if wo.production_id.is_printed:
                    wo.launch_status = 'printed'
                else:
                    wo.launch_status = 'toprint'

    def action_print_mo(self):
        mo_print = self.env['mrp.production']
        for wo in self:
            if not wo.production_id.is_printed:
                mo_print |= wo.production_id
        if mo_print:
            mo_print.write({'is_printed': True})
            return self.env.ref('mrp.action_report_production_order').report_action(mo_print)
