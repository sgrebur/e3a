# integreat greburs

from odoo import fields, models


class StockLocation(models.Model):
    _inherit = "stock.move"

    # after booking each move, when stock becomes negative, we can do autoadjust to 0
    def _action_done(self, cancel_backorder=False):
        self._action_assign()
        for ml in self.move_line_ids.filtered(lambda x: x.location_id.usage == 'view'):
            ml.location_id = ml.location_id.get_warehouse().wh_qc_stock_loc_id

        res = super()._action_done(cancel_backorder=cancel_backorder)

        for move in res:
            negative_quants = move.product_id.stock_quant_ids.filtered(
                    lambda x: x.location_id.usage in ['internal', 'transit'] and x.quantity < 0)
            # adj_location = move.warehouse_id.wh_qc_stock_loc_id
            if negative_quants:
                for quant in negative_quants:
                    auto_adj_vals = quant._get_inventory_move_values(-quant.quantity,
                            quant.product_id.with_company(quant.company_id).property_stock_inventory, quant.location_id)
                    auto_adj_vals['name'] = 'Ajuste Automatico > Stock Negativo'
                    auto_adj_vals['origin'] = move.reference
                    auto_adj_move = self.env['stock.move'].with_context(inventory_mode=False).create(auto_adj_vals)
                    auto_adj_move._action_done()
        return res

    def _action_assign(self):
        super()._action_assign()
        for move in self.filtered(lambda x: x.state not in ['done', 'cancel']):
            wh = move.location_id.get_warehouse()
            if wh:
                stock_loc = move.location_id.get_warehouse().lot_stock_id
                if move.reserved_availability < move.product_uom_qty and move.location_id != stock_loc:
                    move.location_id = stock_loc
                    move.move_line_ids.unlink()
                    move._action_assign()