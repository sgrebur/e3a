# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.tools import float_round
from odoo.exceptions import ValidationError


class ProductQuotationGroupIntegreat(models.Model):
    _name = 'product.quotation.group.integreat'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Product Quotation'
    _check_company_auto = True

    def _default_validity_date(self):
        if self.env['ir.config_parameter'].sudo().get_param('sale.use_quotation_validity_days'):
            days = self.env.company.quotation_validity_days
            if days > 0:
                return fields.Date.to_string(datetime.now() + timedelta(days))
        return fields.Date.to_string(datetime.now() + timedelta(30))

    name = fields.Char(string='# Cotización', required=True, copy=False, readonly=True, index=True, default=lambda self: 'Nuevo')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('checked', 'Verificado'),
        ('sent', 'Enviado'),
        ('confirmed', 'Confirmado'),
        ('rejected', 'Rechazado'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=3, default='draft')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    note = fields.Text('Terms and conditions', compute='_compute_note', store=True, readonly=False)
    validity_date = fields.Date(string='Expiration', readonly=True, copy=False,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, default=_default_validity_date)
    pricelist_id = fields.Many2one('product.pricelist', check_company=True,  # Unrequired company
                                   required=True, readonly=True,
                                   states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                   domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    currency_id = fields.Many2one(related='pricelist_id.currency_id', depends=['pricelist_id'], store=True)
    currency_rate = fields.Float("Currency Rate", compute='_compute_currency_rate', compute_sudo=True, store=True,
                                 digits=(12, 6), readonly=False)
    quot_ids = fields.One2many('product.quotation.integreat', 'group_id')
    is_complete = fields.Boolean('Complete', compute='_compute_group_complete')

    @api.depends('quot_ids.is_complete')
    def _compute_group_complete(self):
        for rec in self:
            rec.is_complete = False
            for quot in rec.quot_ids:
                if quot.is_complete:
                    rec.is_complete = True
                else:
                    rec.is_complete = False
                    break

    @api.model
    def create(self, vals):
        if vals.get('name', 'Nuevo') == 'Nuevo':
            vals['name'] = self.env['ir.sequence'].next_by_code('product.quotation.integreat') or 'New'
        return super().create(vals)

    def unlink(self):
        for rec in self.browse(self.ids):
            if rec.state != 'draft':
                raise ValidationError('¡Está permitido eliminar solo las cotizaciones en estado de borrador!')
        return super().unlink()

    @api.depends('pricelist_id', 'company_id')
    def _compute_currency_rate(self):
        for rec in self:
            if rec.company_id and rec.currency_id and rec.company_id.currency_id != rec.currency_id:  # the following crashes if any one is undefined
                rec.currency_rate = 1 / float_round(self.env['res.currency']._get_conversion_rate(
                    rec.company_id.currency_id, rec.currency_id, rec.company_id, fields.Date.context_today(self)),
                    precision_digits=6)
            else:
                rec.currency_rate = 1

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.pricelist_id = self.partner_id.property_product_pricelist and self.partner_id.property_product_pricelist.id or False

    @api.depends('currency_id', 'partner_id', 'quot_ids.quot_conf_id')
    def _compute_note(self):
        for rec in self:
            if rec.currency_id and rec.partner_id and rec.quot_ids.quot_conf_id:
                if rec.note == '':
                    rec.note = rec.quot_ids.quot_conf_id.quotation_terms.replace('XXX', rec.currency_id.name)
                if rec.note != '':
                    rec.note = rec.note.replace('USD', rec.currency_id.name)
                    rec.note = rec.note.replace('MXN', rec.currency_id.name)
                    x = rec.note.find('FOB')
                    if x > 0:
                        y = rec.note.find('\n', x)
                        if y > x:
                            rec.note = rec.note[:x] + 'FOB su Planta en ' + rec.partner_id.city or '' + ' ' + \
                                    rec.partner_id.state_id.code or '' + ', ' + rec.partner_id.country_id.code or '' \
                                    + '.' + rec.note[y:]
            else:
                rec.note = ''

    def action_create_line(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Open Line',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.quotation.integreat',
            'context': {'default_group_id': self.id},
            'target': 'current',
        }

    def action_quotation_send(self):
        ''' Opens a wizard to compose an email, with relevant mail template loaded by default '''
        self.ensure_one()
        self.write({'state': 'sent'})
        template = self.env.ref('integreat_product_quotation.email_template_quotation_integreat')
        lang = self.partner_id.lang
        if template.lang:
            lang = template._render_lang(self.ids)[self.id]
        ctx = {
            'default_model': 'product.quotation.integreat',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template.id),
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'force_email': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        if self.env.context.get('mark_so_as_sent'):
            self.filtered(lambda o: o.state == 'draft').with_context(tracking_disable=True).write({'state': 'sent'})
        return super(ProductQuotationIntegreat, self.with_context(mail_post_autofollow=True)).message_post(**kwargs)

    def action_quotation_confirm(self):
        self.write({'state': 'confirmed'})
        price_vals = []
        for rec in self.quot_ids.quotation_moq_ids:
            vals = {
                'pricelist_id': rec.quot_id.pricelist_id.id,
                'applied_on': '0_product_variant',
                'base': 'list_price',
                'compute_price': 'fixed',
                'product_id': rec.quot_id.product_id.id,
                'min_quantity': rec.moq,
                'fixed_price': rec.price_unit,
                'date_start': fields.Date.today()
            }
            price_vals.append(vals)
        if price_vals:
            self.env['product.pricelist.item'].create(price_vals)
        for quot in self.quot_ids:
            code = quot.product_id.default_code + ' (' + quot.picking_type_id.warehouse_id.code + ')'
            quot.bom_id.copy(default={'type': 'normal', 'code': code, 'quotation_id': False})

    def action_quotation_print(self):
        self.ensure_one()
        if self.state == 'draft':
            self.write({'state': 'checked'})
        same_tooling_note = self.quot_ids[0].tooling_notes
        for quot in self.quot_ids:
            if quot.tooling_notes != same_tooling_note:
                same_tooling_note = False
                break
        if same_tooling_note:
            self.note += '\n' + same_tooling_note
            self.quot_ids.write({'tooling_notes': False})
        return self.env.ref('integreat_product_quotation.action_report_productquotation').report_action(self)

    def action_quotation_reject(self):
        self.ensure_one()
        self.write({'state': 'rejected'})

    def action_reset_to_draft(self):
        self.ensure_one()
        self.write({'state': 'draft'})


class ProductQuotationIntegreat(models.Model):
    _name = 'product.quotation.integreat'
    _description = 'Product Quotation'
    _check_company_auto = True

    def _default_picking_type(self):
        return self.env['stock.picking.type'].search([
            ('company_id', '=', self.env.company.id),
            ('code', '=', 'mrp_operation')
        ], limit=1)

    name = fields.Char('Name', compute='_compute_name', store=True)
    group_id = fields.Many2one('product.quotation.group.integreat', ondelete='cascade', readonly=True)
    state = fields.Selection(related='group_id.state', store=True)
    company_id = fields.Many2one(related='group_id.company_id', store=True)
    partner_id = fields.Many2one(related='group_id.partner_id', store=True)
    validity_date = fields.Date(related='group_id.validity_date', store=True)
    pricelist_id = fields.Many2one(related='group_id.pricelist_id', store=True)
    currency_id = fields.Many2one(related='group_id.currency_id', store=True)
    currency_rate = fields.Float(related='group_id.currency_rate', store=True)
    quot_line = fields.Integer('Ln')
    is_complete = fields.Boolean('Completo', compute='_compute_is_complete', store=True)
    papel = fields.Char('Papel', compute='_compute_spec_values', store=True)
    flauta = fields.Char('Flauta', compute='_compute_spec_values', store=True)
    recub = fields.Char('Recubrimiento', compute='_compute_spec_values', store=True)
    calibre = fields.Char('Calibre', compute='_compute_spec_values', store=True)
    calibre_search = fields.Many2one('product.attribute.value', 'Calibre ', domain="[('attribute_id.name', '=', 'Calibre')]")
    papel_search = fields.Many2one('product.attribute.value', 'Papel ', domain="[('attribute_id.name', '=', 'Papel')]")
    flauta_search = fields.Many2one('product.attribute.value', 'Flauta ', domain="[('attribute_id.name', '=', 'Flauta')]")
    recub_search = fields.Many2one('product.attribute.value', 'Recubrimiento ', domain="[('attribute_id.name', '=', 'Recubrimiento')]")
    origen = fields.Selection([('NAL', 'NAL'), ('IND', 'IND'), ('HAZ', 'HAZ')], string='Origen', default='NAL')
    ancho_lamina = fields.Integer('Ancho Lamina', compute='_compute_dimensions', store=True)
    largo_lamina = fields.Integer('Largo Lamina', compute='_compute_dimensions', store=True)
    ancho = fields.Integer('Ancho', compute='_convert_uom', store=True, required=True)
    largo = fields.Integer('Largo', compute='_convert_uom', store=True, required=True)
    alto = fields.Integer('Alto', compute='_convert_uom', store=True, required=True)
    ancho_input = fields.Float('Ancho (in)', digits=(12, 2), default=1.0, required=True)
    largo_input = fields.Float('Largo (in)', digits=(12, 2), default=1.0, required=True)
    alto_input = fields.Float('Alto (in)', digits=(12, 2), default=1.0, required=True)
    uom_input = fields.Selection([('mm', 'mm'), ('in', 'in')], default='mm', required=True)
    picking_type_id = fields.Many2one('stock.picking.type', string='Planta por defecto',
        domain="[('code', '=', 'mrp_operation')]", default=_default_picking_type, required=True)
    quot_conf_id = fields.Many2one('product.configuration.integreat', 'Estilo')
    show_button = fields.Integer(compute='_compute_show_button')
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_qty = fields.Integer('Quotation Qty', default=1)
    customer_product_id = fields.Many2one('product.customer.code', compute='_compute_customer_product_id')
    product_code = fields.Char(related='customer_product_id.product_code', readonly=False)
    product_name = fields.Char(related='customer_product_id.product_name', readonly=False)
    drawing_ref = fields.Char('Ref/Drawing')
    bom_id = fields.Many2one('mrp.bom', readonly=True)
    bom_qty = fields.Float(string='Pza/Herr', related='bom_id.product_qty', readonly=False)
    bom_line_ids = fields.One2many('mrp.bom.line', 'quotation_id', readonly=True, states={'draft': [('readonly', False)]})
    cost_material = fields.Float('Costo materiales', digits='Product Price', compute='_compute_cost_and_price', store=True)
    operation_ids = fields.One2many('mrp.routing.workcenter', 'quotation_id', readonly=True, states={'draft': [('readonly', False)]})
    cost_operation = fields.Float('Costo proceso', digits='Product Price', compute='_compute_cost_and_price', store=True)
    suaje = fields.Many2one('mrp.equipment', related='bom_id.suaje', store=True, readonly=False)
    grabado = fields.Many2one('mrp.equipment', related='bom_id.grabado', store=True, readonly=False)
    cost_tooling = fields.Monetary('Costo Herramentales', store=True, readonly=False)
    tooling_buyer = fields.Selection([('customer', 'Cliente'), ('company', 'Econsa')], string='Proveer Herr.',
        default='customer', required=True)
    tooling_notes = fields.Text('Notas', compute='_compute_tooling_note', store=True)
    unit_cost = fields.Monetary('Unit costs', digits='Product Price', compute='_compute_unit_costs', store=True)
    price_sale_qty = fields.Monetary('Venta', digits='Product Price', compute='_compute_cost_and_price')
    price_sale_unit = fields.Monetary('Precio', digits='Product Price', compute='_compute_cost_and_price')
    margin_unit = fields.Char('Margen', compute='_compute_cost_and_price')
    margin_qty = fields.Char('Margen View', compute='_compute_cost_and_price')
    quotation_moq_ids = fields.One2many('product.quotation.line.integreat', 'quot_id', 'MOQ Lines', readonly=True,
        states={'draft': [('readonly', False)]})
    specification_docs = fields.Many2many('ir.attachment', relation='m2m_ir_attachment_product_quotation_rel',
                                          column1='m2m_id', column2='attachment_id', string='Archivos ')

    def button_save_and_return(self):
        return {
            'type': 'ir.actions.act_window_close',
            'effect': 'history_back'
        }

    def unlink(self):
        for rec in self.browse(self.ids):
            if rec.state != 'draft':
                raise ValidationError('¡Está permitido eliminar solo las cotizaciones en estado de borrador!')
        return super().unlink()

    def edit_quotation(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Editar Cotización Producto',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.quotation.integreat',
            'res_id': self.id,
            'context': {'form_view_initial_mode': 'edit'},
        }

    @api.depends('quotation_moq_ids.price_unit')
    def _compute_is_complete(self):
        for quot in self:
            quot.is_complete = False
            moq = quot.quotation_moq_ids.filtered(lambda x: x.price_unit > 0.0)
            if moq:
                quot.is_complete = True

    @api.depends('bom_line_ids.quot_unit_cost', 'operation_ids.quot_unit_cost')
    def _compute_unit_costs(self):
        for rec in self:
            rec.cost_material = sum(rec.bom_line_ids.mapped('quot_unit_cost'))
            rec.cost_operation = sum(rec.operation_ids.mapped('quot_unit_cost'))
            rec.unit_cost = rec.cost_material + rec.cost_operation

    @api.depends('tooling_buyer', 'cost_tooling', 'suaje', 'grabado', 'currency_id')
    def _compute_tooling_note(self):
        for rec in self:
            note = ''
            if rec.suaje:
                note += ' [' + rec.suaje.name + '] ' + rec.suaje.description
            if rec.grabado:
                if note != '':
                    note += '; '
                note += ' [' + rec.grabado.name + '] ' + rec.suaje.description + '; '
            if rec.tooling_buyer:
                if note != '':
                    note += '. '
                if rec.tooling_buyer == 'customer':
                    note += 'Las herramientas serán suministradas por el cliente.'
                elif rec.cost_tooling > 0:
                    value = rec.currency_id.symbol + "{:.0f}".format(rec.cost_tooling)
                    note += 'Costo herramental %s no incluido en precio unitario.' % value
                else:
                    note += 'Costo herramental no incluido en precio unitario.'
            if note != '':
                rec.tooling_notes = note
            else:
                rec.tooling_notes = ''

    @api.depends('uom_input', 'ancho_input', 'largo_input', 'alto_input')
    def _convert_uom(self):
        for rec in self:
            if rec.uom_input == 'in':
                rec.ancho = int(float_round(rec.ancho_input * 25.4, precision_digits=0))
                rec.largo = int(float_round(rec.largo_input * 25.4, precision_digits=0))
                rec.alto = int(float_round(rec.alto_input * 25.4, precision_digits=0))
            else:
                rec.ancho = rec.ancho
                rec.largo = rec.largo
                rec.alto = rec.alto

    @api.depends('product_qty', 'quotation_moq_ids.price_unit')
    def _compute_cost_and_price(self):
        for rec in self:
            moq_id = rec.quotation_moq_ids.filtered(lambda x: x.moq <= rec.product_qty)
            if moq_id:
                moq_id = moq_id[-1]
                rec.price_sale_unit = moq_id.price_unit
                rec.price_sale_qty = rec.price_sale_unit * rec.product_qty
                rec.margin_unit = '   ( Util. ' + rec.currency_id.symbol + ' ' \
                                 + "{:.2f}".format(moq_id.margin_unit) + ' /pza )'
                rec.margin_qty = '   ( Util. ' + rec.currency_id.symbol + ' ' \
                                 + "{:.2f}".format(moq_id.margin_unit * rec.product_qty) + ' /ctd )'
            else:
                rec.price_sale_unit = rec.price_sale_qty = 0
                rec.margin_unit = rec.margin_qty = ''

    @api.depends('product_id')
    def _compute_customer_product_id(self):
        for rec in self:
            if rec.product_id:
                customer_product = self.env['product.customer.code'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('partner_id', '=', rec.partner_id.id)
                ], limit=1)
                if not customer_product:
                    customer_product = self.env['product.customer.code'].create({
                        'product_code': rec.product_code,
                        'product_name': rec.product_name,
                        'product_id': rec.product_id.id,
                        'partner_id': rec.partner_id.id
                    })
                rec.customer_product_id = customer_product
            else:
                rec.customer_product_id = False

    @api.onchange('quot_conf_id', 'uom_input', 'ancho', 'largo', 'alto')
    def _compute_dimensions(self):
        for quot in self:
            if quot.quot_conf_id and all([quot.ancho, quot.largo, quot.alto]):
                l = quot.largo
                w = quot.ancho
                h = quot.alto
                quot.ancho_lamina = eval(quot.quot_conf_id.formula_ancho)
                quot.largo_lamina = eval(quot.quot_conf_id.formula_largo)
            else:
                quot.ancho_lamina = quot.ancho
                quot.largo_lamina = quot.largo
    
    @api.depends('product_id', 'calibre_search', 'papel_search', 'flauta_search', 'recub_search')
    def _compute_spec_values(self):
        for quot in self:
            if quot.product_id:
                quot.calibre = quot.product_id.spec_calibre or False
                quot.papel = quot.product_id.spec_papel or False
                quot.flauta = quot.product_id.spec_flauta or False
                quot.recub = quot.product_id.spec_recub or False
                quot.origen = quot.product_id.spec_origen or False
                quot.ancho_lamina = quot.product_id.spec_ancho or 0
                quot.largo_lamina = quot.product_id.spec_largo or 0
            if quot.calibre_search:
                quot.calibre = quot.calibre_search.name
            if quot.papel_search:
                quot.papel = quot.papel_search.name
            if quot.flauta_search:
                quot.flauta = quot.flauta_search.name
            if quot.recub_search:
                quot.recub = quot.recub_search.name

    @api.onchange('product_id', 'calibre', 'papel', 'flauta', 'recub', 'origen', 'ancho', 'largo',
                  'bom_id', 'price_sale_qty')
    def _compute_show_button(self):
        for rec in self:
            button = 0
            if not rec.product_id and all([rec.calibre, rec.papel, rec.flauta, rec.recub, rec.origen]) \
                    and rec.ancho > 1 and rec.largo > 1:
                button = 1
            elif rec.product_id and not rec.bom_id:
                button = 2
            if rec.bom_id and rec.state == 'draft':
                if rec.bom_line_ids:
                    lamina = rec.bom_line_ids.filtered(lambda x: x.product_id.categ_id == self.env.ref('integreat_sale_product_configurator.lamina'))
                    if lamina:
                        button += 10
                    else:
                        button += 20
                else:
                    button += 20
            rec.show_button = button

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.quot_line = max(res.group_id.quot_ids.mapped('quot_line')) + 1
        return res

    @api.depends('group_id', 'quot_line')
    def _compute_name(self):
        for quot in self:
            if quot.group_id and quot.quot_line:
                quot.name = quot.group_id.name + '/' + str(quot.quot_line)
            else:
                quot.name = 'Nuevo'
    
    def generate_product_data(self):
        self.ensure_one()
        tmpl = self.env.ref('data.prd_tmpl_Box')
        product = self.env['product.product'].search([
            ('product_tmpl_id', '=', tmpl.id),
            ('spec_calibre', '=', self.calibre),
            ('spec_papel', '=', self.papel),
            ('spec_flauta', '=', self.flauta),
            ('spec_recub', '=', self.recub),
            ('uom_caja', '=', self.uom_input),
            ('ancho_caja', '=', self.ancho_input),
            ('largo_caja', '=', self.largo_input),
            ('alto_caja', '=', self.alto_input),
            ('spec_ancho_lamina', '=', self.ancho_lamina),
            ('spec_largo_lamina', '=', self.largo_lamina)
        ], limit=1)
        if product:
            raise ValidationError('Este producto ya existe. \n'
                                  'Considere cambiar el ancho / largo de la lámina con 1 mm. \n'
                                  'Si desea actualizar un producto existente, '
                                  '¡no puede hacerlo a través del proceso de cotización!')
            # self.product_id = product.id
        else:
            conf_vals = {
                'configurator_type': 'box',
                'product_template_id': tmpl.id,
                'pattr1': self.get_ptav_id(tmpl.id, 'Calibre', self.calibre),
                'pattr2': self.get_ptav_id(tmpl.id, 'Papel', self.papel),
                'pattr3': self.get_ptav_id(tmpl.id, 'Flauta', self.flauta),
                'pattr4': self.get_ptav_id(tmpl.id, 'Recubrimiento', self.recub),
                'pcattr1': self.ancho_lamina,
                'pcattr2': self.largo_lamina,
                'lcattr1': self.ancho_lamina,
                'lcattr2': self.largo_lamina,
                'lattr3': self.origen,
                'uom_caja': self.uom_input,
                'ancho_caja': self.ancho_input,
                'largo_caja': self.largo_input,
                'alto_caja': self.alto_input,
                'picking_type_id': self.picking_type_id.id
            }
            conf_wiz = self.env['product.configurator.integreat'].create(conf_vals)
            conf_wiz.with_context(quotation_id=self.id).button_create_product()
            self.product_id = conf_wiz.product_id

    def create_quotation_bom(self):
        bom_tmpl = self.env['mrp.bom'].search([
            ('product_id', '=', self.product_id.id),
            ('picking_type_id', '=', self.picking_type_id.id),
            ('type', '=', 'normal')
        ], limit=1)
        if bom_tmpl:
            self.bom_id = bom_tmpl[0].sudo().copy()
            bom_data = {
                'product_id': self.product_id.id,
                'code': self.name,
                'product_qty': self.bom_qty,
                'picking_type_id': self.picking_type_id.id or False,
                'type': 'quotation',
                'quotation_id': self.id
            }
            tmpl = self.env.ref('data.prd_tmpl_Box')
            lamina = self.env['product.product'].search([
                ('product_tmpl_id', '=', tmpl.id),
                ('spec_calibre', '=', self.calibre),
                ('spec_papel', '=', self.papel),
                ('spec_flauta', '=', self.flauta),
                ('spec_recub', '=', self.recub),
                ('spec_origen', '=', self.origen),
                ('spec_ancho', '=', self.ancho_lamina),
                ('spec_largo', '=', self.largo_lamina)
                ], limit=1)
            if lamina:
                bom_data['bom_line_ids'] = [(0, 0, {
                    'product_id': lamina.id,
                    'product_qty': 1,
                })]
            self.bom_id.sudo().write(bom_data)

    def select_lamina(self):
        vals = {
            'product_id': self.product_id.id,
            'pza_por_herr': self.bom_id.product_qty,
            'qty': self.product_qty,
            'select_single': True,
            'quotation_id': self.id
        }
        wiz = self.env['wizard.lamina.selection'].create(vals)
        wiz.action_compute_lines()
        return wiz.lamina_wizard_action(wiz.id)

    def get_ptav_id(self, tmpl, attrib, value):
        ptav = self.env['product.template.attribute.value']
        attrib_id = self.env['product.attribute'].search([('name', '=', attrib)], limit=1)
        if attrib_id:
            ptav_id = ptav.search([
                ('product_tmpl_id', '=', tmpl),
                ('attribute_id', '=', attrib_id.id),
                ('product_attribute_value_id.name', '=', value)
            ], limit=1)
            if ptav_id:
                return ptav_id.id
        return ptav


class SaleProductConfiguratorIntegreat(models.Model):
    _name = 'product.quotation.line.integreat'
    _description = 'Product Quotation Price Line'
    _order = 'quot_id, moq'

    quot_id = fields.Many2one('product.quotation.integreat', 'Product Quotation')
    currency_id = fields.Many2one(related='quot_id.currency_id')
    moq = fields.Float('MOQ', digits='Product Unit of Measure', default=1)
    unit_cost = fields.Monetary('Costo/pza', related='quot_id.unit_cost')
    cost_additional = fields.Monetary('Correccion +/-', currency_field='currency_id', default=0)
    factor = fields.Float('Factor', default=1.0)
    surface = fields.Float('m2', digits=(12, 3), compute='_compute_moq_prices')
    moq_cost = fields.Monetary('Costo/MOQ', currency_field='currency_id', compute='_compute_moq_prices')
    price_unit = fields.Monetary('PVta', digits='Product Price', compute='_compute_moq_prices', store=True)
    price_moq = fields.Monetary('Venta', digits='Product Price', compute='_compute_moq_prices')
    margin_unit = fields.Monetary('Utilidad', compute='_compute_moq_prices')
    margin_moq = fields.Monetary('Util. Pedido', compute='_compute_moq_prices')
    margin_iva = fields.Monetary('Util. c/iva costo', compute='_compute_moq_prices')

    @api.depends('quot_id.unit_cost', 'quot_id.currency_id', 'quot_id.currency_rate',
                 'moq', 'cost_additional', 'factor')
    def _compute_moq_prices(self):
        for line in self:
            if not line.moq:
                line.moq = 1
            line.surface = float_round(line.quot_id.ancho_lamina * line.quot_id.largo_lamina * line.moq / 1000000, precision_digits=3)
            line.moq_cost = (line.unit_cost + line.cost_additional) * line.moq
            line.price_unit = float_round(line.moq_cost / line.moq * line.factor, precision_digits=2)
            line.price_moq = float_round(line.price_unit * line.moq, precision_digits=2)
            line.margin_unit = line.price_unit - line.moq_cost / line.moq
            line.margin_moq = line.price_moq - line.moq_cost
            line.margin_iva = line.price_moq - line.moq_cost * 1.16
