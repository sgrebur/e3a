# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import float_round


class AccountPayment(models.Model):
    _inherit = "account.payment"

    in_payment_invoice_ids = fields.One2many('account.move', 'in_payment_id', string='Facturas asignadas')
    invoice_discount = fields.Float(string='Discount (%)', digits='Discount', default=0.0)
    amount_unassigned = fields.Monetary(string='Monto disponible', currency_field='currency_id',
        compute='_compute_amount_unassigned')
    reconciled_credit_note_ids = fields.Many2many('account.move', string="Reconciled Credit Notes",
        compute='_compute_cn_buttons',
        help="Credit Notes whose journal items have been reconciled with the invoices assigned to this payment.")
    reconciled_credit_note_count = fields.Integer(string="# Reconciled Credit Notes",
        compute="_compute_cn_buttons")
    balanced_credit_note_ids = fields.Many2many('account.payment', string="Balanced Credit Notes",
        compute='_compute_cn_buttons',
        help="Credit Notes whose journal items have been reconciled with the invoices assigned to this payment.")
    balanced_credit_note_count = fields.Integer(string="# Balanced Credit Notes",
        compute="_compute_cn_buttons")

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        for rec in self:
            if rec.partner_id and rec.partner_type == 'customer':
                rec.amount = 1
                rec.currency_id = rec.partner_id.commercial_partner_id.property_product_pricelist.currency_id
                if rec.journal_id.type == 'bank':
                    rec.l10n_mx_edi_payment_method_id = self.env.ref('l10n_mx_edi.payment_method_transferencia')

    @api.constrains('l10n_mx_edi_payment_method_id', 'amount')
    def _check_mx_payment_method(self):
        for pay in self:
            if pay.company_id:
                if pay.l10n_mx_edi_payment_method_id == self.env.ref('l10n_mx_edi.payment_method_otros') \
                        or not pay.l10n_mx_edi_payment_method_id:
                    raise ValidationError('¡Se debe definir la forma de pago!')
                if pay.amount == 0.0:
                    raise ValidationError('¡El importe del pago debe ser diferente de 0!')


    @api.depends('is_reconciled')
    def _compute_cn_buttons(self):
        for pay in self:
            if pay.is_reconciled and pay.state == 'posted':
                pay.reconciled_credit_note_ids = self.env['account.move'].search([
                    ('move_type', 'in', ('in_refund', 'out_refund')),
                    ('invoice_origin', '=', pay.name)
                ])
                pay.reconciled_credit_note_count = len(pay.reconciled_credit_note_ids)
                pay.balanced_credit_note_ids = self.env['account.payment'].search([
                    ('invoice_origin', '=', pay.name)
                ])
                pay.balanced_credit_note_count = len(pay.balanced_credit_note_ids)
            else:
                pay.reconciled_credit_note_ids = False
                pay.reconciled_credit_note_count = 0
                pay.balanced_credit_note_ids = False
                pay.balanced_credit_note_count = 0

    def button_open_credit_notes(self):
        ''' Redirect the user to the credit note(s) compensated with the invoices reconciled by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Notas de credito"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
        }
        if self.reconciled_credit_note_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.reconciled_credit_note_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.reconciled_credit_note_ids.ids)],
            })
        return action

    def button_open_balanced_payments(self):
        ''' Redirect the user to the credit note(s) compensated with the invoices reconciled by this payment.
        :return:    An action on account.move.
        '''
        self.ensure_one()

        action = {
            'name': _("Pagos Rectificativos"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if self.balanced_credit_note_count == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.balanced_credit_note_ids.id,
            })
        else:
            action.update({
                'view_mode': 'list,form',
                'domain': [('id', 'in', self.balanced_credit_note_ids.ids)],
            })
        return action

    @api.depends('amount', 'in_payment_invoice_ids.in_payment_amount',
                 'in_payment_invoice_ids.in_payment_discount_amount')
    def _compute_amount_unassigned(self):
        for payment in self:
            payment.amount_unassigned = payment.amount \
                - sum(payment.in_payment_invoice_ids.filtered(lambda i: i.move_type in ('in_invoice', 'out_invoice'))
                                                    .mapped('in_payment_amount'))\
                + sum(payment.in_payment_invoice_ids.filtered(lambda i: i.move_type in ('in_refund', 'out_refund'))
                                                    .mapped('in_payment_amount'))\
                - sum(payment.in_payment_invoice_ids.filtered(lambda i: i.journal_id.code == 'MIGR')
                                                    .mapped('in_payment_amount'))

    def action_payment_calculate_discount(self):
        for payment in self:
            invoices = payment.in_payment_invoice_ids.filtered(
                lambda i: i.move_type in ('in_invoice', 'out_invoice') or i.journal_id.code == 'MIGR')
            if payment.invoice_discount > 0.0:
                for move in invoices:
                    move.write({
                        'in_payment_discount_amount':
                            float_round(move.amount_residual * payment.invoice_discount / 100, precision_digits=2)})
            elif payment.invoice_discount == 0.0:
                for move in invoices:
                    move.write({'in_payment_discount_amount': 0.0})

    def action_payment_reconcile_partial(self):
        self.action_post()
        for payment in self:
            # we do this from domain of selected invoices
            different_currencies = payment.in_payment_invoice_ids.filtered(
                lambda i: i.currency_id != payment.currency_id)
            if different_currencies:
                raise ValidationError('¡Esta función no puede conciliar facturas con monedas diferentes a la moneda de pago!')
            amount_list = []
            for move in payment.in_payment_invoice_ids:
                amount_list.append({
                    'id': move.id,
                    'payment': move.in_payment_amount,
                    'discount': move.in_payment_discount_amount
                })
            moves_to_reverse = payment.in_payment_invoice_ids.filtered(lambda m: m.in_payment_discount_amount > 0)
            if moves_to_reverse:
                credit_note = payment._prepare_credit_note_from_payment(moves_to_reverse)
                if credit_note:
                    credit_note.in_payment_amount = 0.0
                    credit_note._post()
                    for move_to_reverse in moves_to_reverse.filtered(lambda i: i.journal_id.code != 'MIGR'):
                        self._reconcile_invoice_with_payment(
                            credit_note, move_to_reverse, amount=move_to_reverse.in_payment_discount_amount
                        )
            credit_notes_to_reconcile = self.in_payment_invoice_ids.filtered(
                lambda i: i.move_type in ('in_refund', 'out_refund'))
            if credit_notes_to_reconcile:
                effective_amount = payment.amount
                payment.amount += sum(credit_notes_to_reconcile.mapped('amount_residual'))
                payment.in_payment_invoice_ids -= credit_notes_to_reconcile
                payment.narration = 'Este pago se ha compensado con las siguientes notas de crédito'
                for cn in credit_notes_to_reconcile:
                    payment.narration += '\nNo. %s | Folio %s | Monto %s -%s' % (
                        cn.name, cn.l10n_mx_edi_cfdi_uuid or 'test', cn.currency_id.name, cn.amount_residual
                    )
                    self._new_payment_reconcile_for_credit_note(cn)
                payment.narration += '\nPor lo tanto, el monto efectivo pagado es: %s %s' % (
                    payment.currency_id.name, effective_amount
                )
            for move in payment.in_payment_invoice_ids:
                for row in amount_list:
                    if row['id'] == move.id:
                        move.in_payment_amount = row['payment']
                        break
                self._reconcile_invoice_with_payment(payment, move, amount=move.in_payment_amount)
                moves_to_reverse.write({'in_payment_discount_amount': 0.0})
            payment.in_payment_invoice_ids = self.env['account.move']

    def _prepare_credit_note_from_payment(self, moves):
        product_serv = self.env.ref('integreat_mx_edi_extended.serv_fact')
        updated_values = {'in_payment_discount_amount': 0.0, 'line_ids': []}
        cn_lines = []
        l10n_mx_edi_origin = '01|'
        for move in moves:
            if move.journal_id.code == 'MIGR':
                company = move.company_id
                for line in move.invoice_line_ids:
                    if line.currency_id != company.currency_id:
                        amount = line.currency_id._convert(
                            line.move_id.in_payment_amount, company.currency_id, company, line.move_id.date
                        )
                    else:
                        amount = line.move_id.in_payment_amount
                    if line.debit > 0.0:
                        updated_values['line_ids'].append((1, line.id, {
                            'amount_currency': line.move_id.in_payment_amount,
                            'debit': amount
                        }))
                    if line.credit > 0.0:
                        updated_values['line_ids'].append((1, line.id, {
                            'amount_currency': -line.move_id.in_payment_amount,
                            'credit': amount
                        }))
                move.write(updated_values)
                move.line_ids._onchange_amount_currency()
                updated_values['line_ids'] = []
            else:
                lines = move.invoice_line_ids.filtered(lambda x: x.price_total > 0.0)
                sum_move = 0.0
                for line in lines:
                    if line == lines[-1]:
                        # TODO: Can remain small value differences? SOLVED HERE???
                        price_unit = line.move_id.in_payment_discount_amount - sum_move
                    else:
                        price_unit = float_round(line.price_total * line.move_id.in_payment_discount_amount
                                                 / line.move_id.amount_total, precision_digits=2)
                        sum_move += price_unit
                    if price_unit >= 0.01:
                        name = line.move_id.name + ' Descuento del monto total: ' \
                               + str(line.price_total) + ' ' + line.currency_id.name + ' | ' + str(line.quantity) + ' ' + \
                               line.product_uom_id.name + ' ' + line.name + ' | Folio Fiscal:' \
                               + (line.move_id.l10n_mx_edi_cfdi_uuid or 'test')
                        tax_ids = []
                        for tax in line.tax_ids:
                            tax_incl = self.env['account.tax'].search([
                                ('company_id', '=', tax.company_id.id),
                                ('type_tax_use', '=', 'sale'),
                                ('amount', '=', tax.amount),
                                ('price_include', '=', True)
                            ])
                            if tax_incl:
                                tax_ids.append(tax_incl.id)
                            else:
                                raise ValidationError('Sales tax configuration as price included tax missing for: \n'
                                                      '- %s' % tax.amount)
                        cn_line = {
                            'product_id': product_serv.id,
                            'product_uom_id': product_serv.uom_id.id,
                            'name': name,
                            'quantity': 1,
                            'price_unit': price_unit,
                            'tax_ids': [(6, 0, tax_ids)],
                        }
                        cn_lines.append((0, 0, cn_line))
            if move.l10n_mx_edi_cfdi_uuid:
                if l10n_mx_edi_origin == '01|':
                    l10n_mx_edi_origin += move.l10n_mx_edi_cfdi_uuid or 'test'
                else:
                    l10n_mx_edi_origin += ',' + move.l10n_mx_edi_cfdi_uuid or 'test'
        if cn_lines:
            journal = self.env['account.move'].with_context(default_move_type='out_refund')._get_default_journal()
            cn_vals = {
                'ref': self.payment_reference or self.name,
                'move_type': self.payment_type == 'outbound' and 'in_refund' or 'out_refund',
                'currency_id': self.currency_id.id,
                'invoice_user_id': self.user_id and self.user_id.id,
                'partner_id': self.partner_id.id,
                'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(
                    self.partner_id.id)).id,
                'journal_id': journal.id,  # company comes from the journal
                'invoice_origin': self.name,
                'invoice_line_ids': cn_lines,
                'company_id': self.company_id.id,
                'invoice_payment_term_id': self.env.ref('account.account_payment_term_immediate').id,
                'l10n_mx_edi_usage': 'G02',
                'l10n_mx_edi_origin': l10n_mx_edi_origin,
                'l10n_mx_edi_payment_method_id': self.env.ref('l10n_mx_edi.payment_method_15').id
            }
            cn = self.env['account.move'].sudo().create([cn_vals])
            return cn

    def _new_payment_reconcile_for_credit_note(self, cn):
        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
        account_id = cn.line_ids.filtered_domain(domain)[0].account_id.id
        payment_vals = {
            'date': cn.date,
            'amount': cn.amount_residual,
            'payment_type': cn.move_type == 'out_refund' and 'outbound' or 'inbound',
            'partner_type': self.partner_type,
            'invoice_origin': self.name,
            'ref': cn.ref,
            'journal_id': self.journal_id.id,
            'currency_id': cn.currency_id.id,
            'partner_id': cn.partner_id.id,
            'partner_bank_id': self.partner_bank_id and self.partner_id.id or False,
            'l10n_mx_edi_payment_method_id': cn.l10n_mx_edi_payment_method_id.id,
            'destination_account_id': account_id
        }
        new_payment = self.env['account.payment'].create(payment_vals)
        new_payment.action_post()
        payment_lines = new_payment.line_ids.filtered_domain(domain)
        for account in payment_lines.account_id:
            move_lines = cn.line_ids.filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])
            (payment_lines + move_lines).reconcile()

    def _reconcile_invoice_with_payment(self, payment, moves, amount=0.0):
        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
        migration_invoices = moves.filtered(lambda i: i.journal_id.code == 'MIGR')
        if migration_invoices:
            migration_invoices.action_post()
        payment_lines = payment.line_ids.filtered_domain(domain)
        for move in moves:
            for account in payment_lines.account_id:
                m_lines = move.line_ids.filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])
                p_lines = payment_lines.filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)])
                if len(m_lines) == 1 and len(p_lines) == 1:
                    (p_lines + m_lines).with_context(
                        credit_line_id=p_lines[0].id, debit_line_id=m_lines[0].id, amount=amount
                    ).reconcile()
                else:
                    raise ValidationError('No es posible conciliar automáticamente facturas'
                                          ' con múltiples líneas de tipo cuentas por '
                                          'cobrar / pagar. (Factura: %s)' % move.name)
        return True


class AccountPartialReconcile(models.Model):
    _inherit = "account.partial.reconcile"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            credit_line_id = self._context.get('credit_line_id', False)
            debit_line_id = self._context.get('debit_line_id', False)
            amount = self._context.get('amount', 0.0)
            debit_id = vals.get('debit_move_id', False)
            credit_id = vals.get('credit_move_id', False)
            if credit_line_id and debit_line_id and amount > 0.0 \
                    and credit_id == credit_line_id and debit_id == debit_line_id:
                vals.update({'amount': amount, 'debit_amount_currency': amount, 'credit_amount_currency': amount})
        return super(AccountPartialReconcile, self).create(vals_list)
