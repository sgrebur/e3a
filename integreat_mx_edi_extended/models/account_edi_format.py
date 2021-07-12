# -*- coding: utf-8 -*-

from odoo import api, models, fields, tools, _

import re
from datetime import datetime
from lxml import etree, objectify


class AccountEdiFormat(models.Model):
    _inherit = 'account.edi.format'

    def _is_compatible_with_journal(self, journal):
        # OVERRIDE
        self.ensure_one()
        if self.code != 'cfdi_3_3':
            return super()._is_compatible_with_journal(journal)
        return (journal.type == 'sale' or journal.code == 'MIGR') and journal.country_code == 'MX'

    @api.model
    def _l10n_mx_edi_get_serie_and_folio(self, move):
        if move.journal_id.code == 'MIGR':
            name_numbers = list(re.finditer('\d+', move.ref))
            serie_number = move.ref[:name_numbers[-1].start()]
            folio_number = name_numbers[-1].group().lstrip('0')
            return {
                'serie_number': serie_number,
                'folio_number': folio_number,
            }
        else:
            return super()._l10n_mx_edi_get_serie_and_folio(move)

    def _create_invoice_from_attachment(self, attachment):
        res = super()._create_invoice_from_attachment(attachment)
        if res:
            attachment.write({'res_id': res.id, 'edi_import_status': 'done'})
            # self.env.cr.commit()
        else:
            attachment.write({'edi_import_status': 'error'})
            # self.env.cr.commit()
        return res

    def _update_invoice_from_attachment(self, attachment, invoice):
        res = super()._update_invoice_from_attachment(attachment, invoice)
        if res:
            if res.line_ids:
                attachment.write({'edi_import_status': 'done'})
                # self.env.cr.commit()
            else:
                attachment.write({'edi_import_status': 'error'})
                # self.env.cr.commit()
        return res

    def _is_cfdi_vendor_bill(self, tree):
        if self.code == 'cfdi_3_3' and tree.tag == '{http://www.sat.gob.mx/cfd/3}Comprobante':
            return True

    def _create_invoice_from_xml_tree(self, filename, tree):
        self.ensure_one()
        if self._is_cfdi_vendor_bill(tree):
            invoice = self._import_cfdi_vendor_bill(filename, tree, self.env['account.move'])
            return invoice
        res = super()._create_invoice_from_xml_tree(filename, tree)
        return res

    def _update_invoice_from_xml_tree(self, filename, tree, invoice):
        self.ensure_one()
        if self._is_cfdi_vendor_bill(tree):
            invoice = self._import_cfdi_vendor_bill(filename, tree, invoice)
            return invoice
        res = super()._update_invoice_from_xml_tree(filename, tree, invoice)
        return res

    def _import_cfdi_vendor_bill(self, filename, tree, invoice):
        """ Decodes a CFDI invoice into an invoice.

        :param tree:    the cfdi tree to decode.
        :param invoice: the invoice to update or an empty recordset.
        :returns:       the invoice where the cfdi data was imported.
        """
        # convert back to string, than objectify
        self = self.with_user(self.env.ref('base.partner_root').id)
        error_msg = '<ul class="text-danger">Importar %s no es posible:' % filename

        invoice = invoice
        original_invoice = self.env['account.move']
        if invoice and invoice.line_ids:
            original_invoice = invoice
            invoice = self.env['account.move']

        xml = objectify.fromstring(etree.tostring(tree))

        if xml.attrib['TipoDeComprobante'] == 'I':
            move_type = 'in_invoice'
        elif xml.attrib['TipoDeComprobante'] == 'E':
            move_type = 'in_refund'
        else:
            error_msg += '<li>El tipo de comprobante no es I(ngreso) o E(greso)</li></ul>'
            invoice = self._post_import_error_message(error_msg, original_invoice, invoice)
            return invoice
        # load demo RFC if in test mode
        if xml.Receptor.attrib['Rfc'] not in (self.env.company.vat, self.env.company.company_registry, 'XAXX010101000', 'XEXX010101000'):
            error_msg += '<li>El receptor está mal: %s RFC: %s</li></ul>' % (xml.Receptor.attrib['Nombre'], xml.Receptor.attrib['Rfc'])
            invoice = self._post_import_error_message(error_msg, original_invoice, invoice)
            return invoice

        success_msg = ''
        journal = self.env['account.move'].with_context(default_move_type='in_invoice')._get_default_journal()
        vendor = self.env['res.partner'].search([('vat', '=', xml.Emisor.attrib['Rfc'])], limit=1)
        if not vendor:
            vendor = self.env['res.partner'].create({
                'name': xml.Emisor.attrib['Nombre'],
                'zip': xml.attrib['LugarExpedicion'],
                'vat': xml.Emisor.attrib['Rfc'],
                'company_type': 'company',
                'type': 'contact'
            })
            # this is not an error message
            success_msg += '<p>Se ha creado un nuevo proveedor:' \
                           '<a href=# data-oe-model=account.move data-oe-id=%d>%s</a></br>' \
                           'Por favor, verifique los datos de contacto.</p>' % (vendor.id, vendor.name)
        ref = ''
        if xml.attrib.get('Serie', False):
            ref = xml.attrib['Serie']
        if xml.attrib.get('Folio', False):
            ref += xml.attrib['Folio']
        if hasattr(xml, 'Complemento'):
            uuid = xml.Complemento.xpath(
                'tfd:TimbreFiscalDigital[1]', namespaces={'tfd': 'http://www.sat.gob.mx/TimbreFiscalDigital'}
            )[0].attrib.get('UUID')
        if ref == '':
            ref = uuid
        currency = xml.attrib['Moneda']
        if currency == 'XXX':
            currency = 'MXN'
        currency_id = self._retrieve_currency(currency)
        if not currency_id:
            error_msg += '<li>La moneda %s no está activada en el sistema</li></ul>' % currency
            invoice = self._post_import_error_message(error_msg, original_invoice, invoice)
            return invoice
        invoice_date = datetime.strptime(xml.attrib['Fecha'], '%Y-%m-%dT%H:%M:%S')

        # check if same ref already exists... this would be a constraint error later on creation
        old_invoice = self.env['account.move'].search([
            ('move_type', '=', move_type),
            ('partner_id', '=', vendor.id),
            ('ref', '=', ref),
            ('state', '!=', 'cancel')
        ], limit=1)
        if old_invoice:
            error_msg += '<p>Ya existe una factura con la misma referencia para el proveedor %s: ' \
                         '<a href=# data-oe-model=account.move data-oe-id=%d>%s</a></p>' \
                         % (vendor.name, old_invoice[0].id, old_invoice[0].name)
            invoice = self._post_import_error_message(error_msg, original_invoice, invoice)
            return invoice

        invoice_line_vals = []
        seq = 0
        for line in xml.Conceptos.Concepto:
            # treat first tax ids
            tax_ids = []
            if hasattr(line, 'Impuestos'):
                for impuesto in line.Impuestos:
                    if hasattr(impuesto, 'Traslados'):
                        for traslado in line.Impuestos.Traslados.Traslado:
                            if traslado.attrib['TipoFactor'] != 'Exento':
                                tax_group = {'001': 'ISR Traslado', '002': 'IVA Traslado', '003': 'IEPS Traslado'}. \
                                    get(traslado.attrib['Impuesto'])
                                tax = self.env['account.tax'].search([
                                    ('company_id', '=', self.env.company.id),
                                    ('type_tax_use', '=', journal.type),
                                    ('tax_group_id.name', '=', tax_group),
                                    ('amount', '=', float(traslado.attrib['TasaOCuota']) * 100),
                                ], limit=1)
                                if not tax:
                                    error_msg += '<li>El impuesto TRASLADO no está configurado en el sistema: ' \
                                                 'Impuesto=%s TipoFactor=%s TasaOCuota=%s</li></ul>' \
                                                 % (traslado.attrib['Impuesto'], traslado.attrib['TipoFactor'],
                                                    traslado.attrib['TasaOCuota'])
                                    invoice = self._post_import_error_message(error_msg, original_invoice, invoice)
                                    return invoice
                                tax_ids.append(tax.id)
                    if hasattr(impuesto, 'Retenciones'):
                        for retencion in line.Impuestos.Retenciones.Retencion:
                            tax_group = {'001': 'ISR Retenido', '002': 'IVA Retenido', '003': 'IEPS Retenido'}. \
                                get(retencion.attrib['Impuesto'])
                            tax = self.env['account.tax'].search([
                                ('company_id', '=', self.env.company.id),
                                ('type_tax_use', '=', journal.type),
                                ('tax_group_id.name', '=', tax_group),
                                ('amount', '=', -float(retencion.attrib['TasaOCuota']) * 100),
                            ], limit=1)
                            if not tax:
                                error_msg += '<li>El impuesto de RETENCION no está configurado en el sistema: ' \
                                             'Impuesto=%s TipoFactor=%s TasaOCuota=%s</li></ul>' \
                                             % (retencion.attrib['Impuesto'], retencion.attrib['TipoFactor'],
                                                retencion.attrib['TasaOCuota'])
                                invoice = self._post_import_error_message(error_msg, original_invoice, invoice)
                                return invoice
                            tax_ids.append(tax.id)
            seq += 1
            code = False
            if line.get('NoIdentificacion', False):
                code = line.attrib['NoIdentificacion']
            product = self._search_product(vendor, code, line.attrib['Descripcion'], line.attrib['ClaveProdServ'])
            if line.get('Descuento', False):
                discount = float(line.attrib['Descuento']) / float(line.attrib['Importe']) * 100
            else:
                discount = False
            invoice_line_vals.append((0, 0, {
                'sequence': seq,
                'name': line.attrib['Descripcion'],
                'product_id': product and product.id or False,
                'product_uom_id': product and product.uom_po_id.id or False,
                'quantity': float(line.attrib['Cantidad']),
                'discount': discount,
                'price_unit': float(line.attrib['ValorUnitario']),
                'tax_ids': [(6, 0, tax_ids)],
                # 'analytic_account_id': xid,
                # 'analytic_tag_ids': [(6, 0, xid)],
            }))
        invoice_vals = {
            'company_id': self.env.company.id,
            'ref': ref,
            'move_type': move_type,
            'invoice_date': invoice_date,
            'currency_id': currency_id.id,
            'partner_id': vendor.id,
            'invoice_payment_term_id': vendor.property_supplier_payment_term_id.id,
            'journal_id': journal.id,
            'invoice_line_ids': invoice_line_vals,
            'narration': 'UUID: ' + uuid,
        }
        if invoice:
            invoice.write(invoice_vals)
        else:
            invoice = invoice.with_context(default_move_type=move_type).create([invoice_vals])
        # self.env.cr.commit()
        if success_msg:
            invoice.message_post(body=success_msg)
        return invoice

    def _post_import_error_message(self, msg, original_invoice, invoice):
        if original_invoice:
            original_invoice.message_post(body=msg)
            return original_invoice
        elif invoice:
            invoice.message_post(body=msg)
            return invoice
        else:
            new_invoice = self.env['account.move'].with_user(self.env.ref('base.partner_root').id).create({'move_type': 'in_invoice'})
            new_invoice.with_user(self.env.ref('base.partner_root').id).message_post(body=msg)
            return new_invoice

    def _search_product(self, vendor, code, descr, clave):
        product = self.env['product.product']
        if code:
            product = product.search([('default_code', '=', code)], limit=1)
        if not product:
            product = product.search([
                '|',
                ('default_code', '=', descr),
                ('name', 'ilike', descr)
            ], limit=1)
        if not product:
            seller_id = self.env['product.supplierinfo'].search([
                ('name', '=', vendor.id),
                '|',
                ('product_code', '=', code),
                ('product_name', 'ilike', descr)
            ], limit=1)
            if seller_id:
                product = seller_id.product_id
        if not product:
            for n in range(8, 1, -1):
                product = product.search([
                    ('l10n_mx_edi_clave_search_pattern', '!=', False),
                    ('l10n_mx_edi_clave_search_pattern', 'like', clave[:n])
                ], limit=1)
                if product:
                    break
        if not product:
            # TODO company check
            journal_id = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
            product = product.search([
                ('type', '=', 'service'),
                ('property_account_expense_id', '=', journal_id.default_account_id)
            ], limit=1)
        return product
