# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import os
import logging
_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    edi_import_status = fields.Selection([('todo', 'To be processed'), ('done', 'Imported'), ('error', 'Processed with error')],
        string='EDI Import Status', help='Attachment EDI import processing status. If not relevant, than False')


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_default_l10n_mx_sat_status(self):
        if self.env.company.l10n_mx_edi_pac_test_env:
            return 'test'
        else:
            return 'undefined'

    l10n_mx_edi_cfdi_request = fields.Selection(selection_add=[('migration', 'Migration')],
        ondelete={'migration': lambda r: r.write({'l10n_mx_edi_cfdi_request': False})})
    l10n_mx_edi_sat_status = fields.Selection(selection_add=[('test', 'Test')], default=_get_default_l10n_mx_sat_status,
        ondelete={'test': lambda r: r.write({'l10n_mx_edi_sat_status': 'undefined'})})
    l10n_mx_edi_leyenda = fields.Boolean(related='partner_id.l10n_mx_edi_leyenda', store=True)
    l10n_mx_edi_leyenda_texto = fields.Text(related='partner_id.l10n_mx_edi_leyenda_texto', store=True)
    l10n_mx_edi_leyenda_norma = fields.Char(related='partner_id.l10n_mx_edi_leyenda_norma', store=True)
    l10n_mx_edi_leyenda_disposicion = fields.Char(related='partner_id.l10n_mx_edi_leyenda_disposicion', store=True)
    edi_xml_to_import = fields.Boolean('XML to be imported', compute='_compute_edi_xml_to_import')
    in_payment_id = fields.Many2one('account.payment')
    payment_partial_select = fields.Boolean('Selected')
    in_payment_amount = fields.Monetary('Monto Pagado', compute='_compute_in_payment_amount',
        currency_field='currency_id', store=True, readonly=False)
    in_payment_discount_amount = fields.Monetary('Monto Descuento', default=0.0, currency_field='currency_id')
    in_payment_amount_residual = fields.Monetary('Saldo Pendiente', compute='_compute_in_payment_amount_residual',
        currency_field='currency_id', store=True, readonly=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', compute='_compute_company_id',
        store=True, readonly=True, default=lambda self: self.env.company)
    migration_invoice_value = fields.Monetary('Monto Original Factura', currency_field='currency_id')
    # we duplicate it in db from the inheritance account.payment, but required for sequence sql
    payment_partner_type = fields.Selection(related='payment_id.partner_type', store=True)

    # other sequence for customer and supplier payments
    def _get_last_sequence_domain(self, relaxed=False):
        where_string, param = super(AccountMove, self)._get_last_sequence_domain(relaxed)
        if self.payment_partner_type:
            where_string += " AND payment_partner_type = %(payment_partner_type)s"
            param['payment_partner_type'] = self.payment_partner_type
        return where_string, param

    # OVERRIDE ...
    @api.depends('edi_document_ids')
    def _compute_cfdi_values(self):
        super()._compute_cfdi_values()
        for move in self:
            if move.journal_id.code == 'MIGR':
                move.l10n_mx_edi_cfdi_uuid = move.narration

    # OVERRIDE ... it is used only for EDI/printout???
    def _get_reconciled_invoices(self):
        """Helper used to retrieve the reconciled payments on this journal entry"""
        reconciled_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        reconciled_amls = reconciled_lines.mapped('matched_debit_ids.debit_move_id') + \
                          reconciled_lines.mapped('matched_credit_ids.credit_move_id')
        return reconciled_amls.move_id.filtered(
            lambda move: move.is_invoice(include_receipts=True) or move.journal_id.code == 'MIGR')

    @api.depends('move_type', 'company_id', 'journal_id.code')
    def _compute_l10n_mx_edi_cfdi_request(self):
        super()._compute_l10n_mx_edi_cfdi_request()
        for move in self:
            if move.journal_id.code == 'MIGR':
                move.l10n_mx_edi_cfdi_request = 'migration'

    @api.depends('edi_document_ids.state')
    def _compute_edi_state(self):
        super()._compute_edi_state()
        for move in self:
            if move.journal_id.code == 'MIGR':
                move.edi_state = 'sent'
    
    def _l10n_mx_edi_decode_cfdi(self, cfdi_data=None):
        res = super()._l10n_mx_edi_decode_cfdi(cfdi_data=cfdi_data)
        if cfdi_data and self.l10n_mx_edi_leyenda:
            res['cfdi_node'].attrib['{http://www.w3.org/2001/XMLSchema-instance}schemaLocation'] += \
                ' http://www.sat.gob.mx/leyendasFiscales' \
                ' http://www.sat.gob.mx/sitio_internet/cfd/leyendasFiscales/leyendasFisc.xsd'
        return res

    # OVERRIDE: MIGR amount_residual
    @api.depends(
        'line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual',
        'line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency',
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'line_ids.full_reconcile_id',
        'journal_id.code')
    def _compute_amount(self):
        super()._compute_amount()
        for move in self:
            if move.journal_id.code == 'MIGR':
                receivable_lines = move.line_ids.filtered_domain(
                    [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                )
                if receivable_lines:
                    debit = sum(receivable_lines.mapped('amount_currency'))
                    reconciled = sum(receivable_lines.matched_credit_ids.mapped('credit_amount_currency'))
                    move.amount_residual = debit - reconciled
                else:
                    move.amount_residual = 0.0

    @api.depends('in_payment_id', 'in_payment_discount_amount', 'journal_id.code')
    def _compute_in_payment_amount(self):
        for move in self:
            if move.in_payment_id:
                move.in_payment_amount = move.amount_residual - move.in_payment_discount_amount
            else:
                move.in_payment_amount = 0.0

    @api.depends('in_payment_amount')
    def _compute_in_payment_amount_residual(self):
        for move in self:
            if move.in_payment_amount > 0 or move.in_payment_discount_amount > 0:
                move.in_payment_amount_residual = move.amount_residual - move.in_payment_amount - move.in_payment_discount_amount
                if move.in_payment_amount_residual < 0:
                    raise ValidationError('¡El pago y el descuento no pueden ser inferiores al monto adeudado!')
            else:
                move.in_payment_amount_residual = 0

    def l10n_mx_edi_update_sat_status(self):
        if self.env.company.l10n_mx_edi_pac_test_env:
            self.l10n_mx_edi_sat_status = 'test'
        else:
            return super().l10n_mx_edi_update_sat_status()

    # OVERRIDE
    @api.depends('move_type', 'invoice_date_due', 'invoice_date', 'invoice_payment_term_id',
                 'invoice_payment_term_id.line_ids')
    def _compute_l10n_mx_edi_payment_policy(self):
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund', 'out_receipt') and move.invoice_date_due and move.invoice_date:
                # In CFDI 3.3 - rule 2.7.1.43 which establish that
                # invoice payment term should be PPD as soon as the due date
                # is after the last day of  the month (the month of the invoice date).
                ### OVERRIDE: logic changed (if not same day or immediate payment term)
                if (move.invoice_date_due != move.invoice_date and
                        move.invoice_payment_term_id != self.env.ref('account.account_payment_term_immediate')) \
                        or len(move.invoice_payment_term_id.line_ids) > 1:  # to be able to force PPD
                    move.l10n_mx_edi_payment_policy = 'PPD'
                else:
                    move.l10n_mx_edi_payment_policy = 'PUE'
            elif move.journal_id.code == 'MIGR':
                move.l10n_mx_edi_payment_policy = 'PPD'
            else:
                move.l10n_mx_edi_payment_policy = False

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        for move in self:
            if move.move_type in ('out_invoice', 'out_receipt', 'out_refund'):
                # PRICE < 0.01 min allowed for CFDI
                for line in move.invoice_line_ids:
                    if (line.price_unit < 0.01 or line.price_subtotal < 0.01) and not line.display_type:
                        raise ValidationError('No se permite la línea de factura con precio/valor inferior a 0,01. \n'
                                              'Puede facturar un valor superior a 0,01 y crear una nota de crédito '
                                              'para el valor total como descuento.')
                # CFDI forma de pago rules
                if move.l10n_mx_edi_payment_policy == 'PUE' \
                        and (move.l10n_mx_edi_payment_method_id == self.env.ref('l10n_mx_edi.payment_method_otros')
                             or not move.l10n_mx_edi_payment_method_id):
                    raise ValidationError('Metodo de pago es PUE: ¡Se debe definir la forma de pago!')
                elif move.l10n_mx_edi_payment_policy == 'PPD' \
                        and move.l10n_mx_edi_payment_method_id != self.env.ref('l10n_mx_edi.payment_method_otros'):
                    raise ValidationError('Metodo de pago es PPD: ¡Forma de pago debe ser 99 - Por definir!')
        return res

    @api.model
    def _get_invoice_in_payment_state(self):
        # OVERRIDE to enable the 'in_payment' state on invoices.
        # we don't need for this customer the bank reconciliation, therefore no sense for in payment
        return 'paid'

    def _get_sale_order_for_printout(self):
        for move in self:
            order_list = list(dict.fromkeys(move.line_ids.sale_line_ids.mapped('order_id.name')))
            if len(order_list) == 1:
                if move.line_ids[0].sale_line_ids[0].order_id.client_order_ref:
                    return move.line_ids[0].sale_line_ids[0].order_id.client_order_ref
                else:
                    return move.line_ids[0].sale_line_ids[0].order_id.name
            elif len(order_list) > 1:
                return 'MULTI'
            else:
                return 'NONE'

    @api.depends('attachment_ids.edi_import_status', 'move_type', 'state')
    def _compute_edi_xml_to_import(self):
        for move in self:
            if move.attachment_ids and move.move_type == 'in_invoice' and move.state == 'draft':
                todo_xml_files = move.attachment_ids.filtered(
                    lambda a: 'xml' in a.name.lower() and (not a.edi_import_status or a.edi_import_status == 'todo'))
                if todo_xml_files:
                    move.edi_xml_to_import = True
                else:
                    move.edi_xml_to_import = False
            else:
                move.edi_xml_to_import = False

    def process_attachment_edi_xml_invoice_import(self):
        self = self.with_user(self.env.ref('base.partner_root').id)
        invoice = self.env['account.move']
        draft_bills = self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('move_type', '=', 'in_invoice'),
            ('attachment_ids', '!=', False)
        ])
        if draft_bills:
            todo_xml_files = draft_bills.attachment_ids.filtered(lambda a: 'xml' in a.mimetype and not a.edi_import_status)
            if not todo_xml_files:
                return
            todo_xml_files.write({'edi_import_status': 'todo'})
            # self.env.cr.commit()
        else:
            return

        moves = self.env['account.move'].browse(list(set(todo_xml_files.mapped('res_id'))))

        for move in moves:
            xml_files = move.attachment_ids.filtered(lambda a: a.edi_import_status == 'todo')
            decoders_update = self._get_update_invoice_from_attachment_decoders(move)
            # decoders_create = self._get_create_invoice_from_attachment_decoders()
            while not move.line_ids:
                for xml_file in xml_files:
                    for decoder in sorted(decoders_update, key=lambda d: d[0]):
                        invoice = decoder[1](xml_file, move)
                        if invoice:
                            move = self.env['account.move'].search([('id', '=', todo_xml_files[0].res_id)])
                            break
                    if invoice:
                        invoice.message_post(body=_('La factura se ha importado de un archivo xml: %s.') % xml_file.name)
                        self.env.cr.commit()
                        break
                # redo filtering for the attachment processed in this loop
                xml_files = move.attachment_ids.filtered(lambda a: a.edi_import_status == 'todo')
            pdf_files = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', move.id),
                ('edi_import_status', '=', False),
                ('mimetype', '=', 'application/pdf')
            ])
            new_invoices = self.env['account.move']
            for xml_file in xml_files:
                for decoder in sorted(decoders_update, key=lambda d: d[0]):
                    invoice = decoder[1](xml_file, move)
                    if invoice:
                        invoice.message_post(body='<p class="text-danger">'
                            'Esta factura es el resultado de la importación de archivos XML adjuntos a la factura:'
                            '<a href=# data-oe-model=account.move data-oe-id=%d>%s</a></br>'
                            'El mensaje original tiene varios archivos adjuntos que se dividieron en diferentes facturas.'
                            '</p>' % (move.id, move.name))
                        # self.env.cr.commit()
                        if pdf_files:
                            filename = os.path.splitext(xml_file.name)
                            pdf_file = pdf_files.filtered(lambda f: filename[0] in f.name)
                            if pdf_file:
                                pdf_file[0].write({'res_id': invoice.id})
                                # self.env.cr.commit()
                        new_invoices += invoice
            if new_invoices:
                text = ''
                for inv in new_invoices:
                    text = '%s<li><a href=# data-oe-model=account.move data-oe-id=%d>%s</a>(%s)</li>' % (
                    text, inv.id, inv.ref, inv.partner_id.name)
                move.message_post(body=_('<div>Other invoices have been created from the original message:<ul>'
                    + text + '</ul></div>'))
                # self.env.cr.commit()


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_line_sale_order_for_printout(self):
        self.ensure_one()
        line_order_reference = ''
        for order in self.sale_line_ids.mapped('order_id'):
            if order.client_order_ref:
                line_order_reference += order.client_order_ref
        return line_order_reference

    def _get_description_for_printout(self):
        self.ensure_one()
        if self.product_id and self.move_id.move_type != 'out_refund' and self.move_id.l10n_mx_edi_usage != 'G02' :
            if self.move_id.partner_id.commercial_partner_id != self.move_id.partner_id:
                partner = self.move_id.partner_id.commercial_partner_id.id
            else:
                partner = self.move_id.partner_id.id
            description = self.product_id._get_partner_code_name(self.product_id, partner)
            if description['code'] != self.product_id.default_code:
                description['int_ref'] = self.product_id.default_code
            else:
                description['int_ref'] = 'NONE'
        else:
            description = {'code': 'NONE', 'name': self.name, 'int_ref': 'NONE'}
        return description
