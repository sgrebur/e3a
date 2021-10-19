# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_round


class SaleProductConfiguratorIntegreat(models.TransientModel):
    _name = 'product.configurator.integreat'
    _description = 'Product Configurator'

    parent_wiz_id = fields.Many2one('product.configurator.integreat')
    product_model = fields.Many2one('product.product', 'Tipo Producto', domain="[('is_model', '=', True)]")
    product_model_tmpl = fields.Many2one(related='product_model.product_tmpl_id')
    model_code = fields.Char(related='product_model.default_code')
    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)
    prd_name = fields.Char('Descripción producto')
    prd_code = fields.Char('Referencia interna')
    prd_unspsc = fields.Many2one('product.unspsc.code', 'Clave SAT (UNSPSC)')
    product_id_name = fields.Char(related='product_id.name', readonly=False, translate=True)
    product_id_unpsc = fields.Many2one(related='product_id.unspsc_code_id', readonly=False)
    sale_ok = fields.Boolean(string='Puede ser vendido')
    purchase_ok = fields.Boolean(string='Puede ser comprado')
    product_id_sale_ok = fields.Boolean(related='product_id.sale_ok', readonly=False)
    product_id_purchase_ok = fields.Boolean(related='product_id.purchase_ok', readonly=False)
    product_id_image_1920 = fields.Image(related='product_id.image_1920', readonly=False)
    product_style = fields.Many2one('product.configuration.integreat', 'Estilo', domain="[('product_model_ids', '=', product_model)]")
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    calibre = fields.Char('Calibre', compute='_compute_spec_values', store=True)
    papel = fields.Char('Papel', compute='_compute_spec_values', store=True)
    flauta = fields.Char('Flauta', compute='_compute_spec_values', store=True)
    recub = fields.Char('Recubrimiento', compute='_compute_spec_values', store=True)
    calibre_search = fields.Many2one('product.attribute.value', 'Calibre ', domain="[('attribute_id.name', '=', 'Calibre')]")
    papel_search = fields.Many2one('product.attribute.value', 'Papel ', domain="[('attribute_id.name', '=', 'Papel')]")
    flauta_search = fields.Many2one('product.attribute.value', 'Flauta ', domain="[('attribute_id.name', '=', 'Flauta')]")
    recub_search = fields.Many2one('product.attribute.value', 'Recubrimiento ', domain="[('attribute_id.name', '=', 'Recubrimiento')]")
    tipo_tinta_search = fields.Many2one('product.attribute.value', 'Tipo tinta ', domain="[('attribute_id.name', '=', 'Tipo Tinta')]")
    color_search = fields.Many2one('product.attribute.value', 'Color ', domain="[('attribute_id.name', '=', 'Color')]")
    origen = fields.Selection([('NAL', 'NAL'), ('IND', 'IND'), ('HAZ', 'HAZ')], string='Origen', default='NAL')
    ancho_lamina = fields.Integer('Ancho Lamina')
    largo_lamina = fields.Integer('Largo Lamina')
    ancho = fields.Integer('Ancho', compute='_convert_uom', store=True, readonly=False)
    largo = fields.Integer('Largo', compute='_convert_uom', store=True, readonly=False)
    alto = fields.Integer('Alto', compute='_convert_uom', store=True, readonly=False)
    ancho_input = fields.Float('Ancho (in)', digits=(12, 2), default=0)
    largo_input = fields.Float('Largo (in)', digits=(12, 2), default=0)
    alto_input = fields.Float('Alto (in)', digits=(12, 2), default=0)
    uom_input = fields.Selection([('mm', 'mm'), ('in', 'in')], default='mm', required=True)
    marca1 = fields.Char(string='Marca 1')
    marca2 = fields.Char(string='Marca 2')
    marca3 = fields.Char(string='Marca 3')
    picking_type_id = fields.Many2one('stock.picking.type', string='Planta por defecto',
        domain="[('code', '=', 'mrp_operation')]")
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id')
    partner_id = fields.Many2one('res.partner', 'Cliente')
    customer_product_id = fields.Many2one('product.customer.code', compute='_compute_customer_product_id')
    customer_product_code = fields.Char(related='customer_product_id.product_code', readonly=False)
    customer_product_name = fields.Char(related='customer_product_id.product_name', readonly=False)
    product_code = fields.Char('Codigo Producto Cliente')
    product_name = fields.Char('Descripcion Producto Cliente')
    partner_pricelist_id = fields.Many2one(related='partner_id.property_product_pricelist')
    pricelist_items_model = fields.Many2many(comodel_name='product.pricelist.item',
        relation='product_configurator_integreat_product_model_pricelist_item_rel', column1='m2m_id', column2='item_id')
    pricelist_items = fields.Many2many(comodel_name='product.pricelist.item',
        relation='product_configurator_integreat_product_pricelist_item_rel', column1='m2m_id', column2='item_id',
        store=True, compute='_compute_spec_values', readonly=False)
    supplierinfos_model = fields.Many2many(comodel_name='product.supplierinfo',
        relation='product_configurator_integreat_product_model_supplierinfo_rel', column1='m2m_id', column2='info_id')
    supplierinfos = fields.Many2many(comodel_name='product.supplierinfo',
        relation='product_configurator_integreat_product_supplierinfo_rel', column1='m2m_id', column2='info_id',
        store=True, compute='_compute_spec_values', readonly=False)
    bom_id = fields.Many2one('mrp.bom')
    bom_qty = fields.Float(related='bom_id.product_qty', readonly=False)
    bom_picking_type_id = fields.Many2one(related='bom_id.picking_type_id', readonly=False)
    suaje = fields.Many2one(related='bom_id.suaje', readonly=False)
    grabado = fields.Many2one(related='bom_id.grabado', readonly=False)
    bom_line_ids = fields.One2many(related='bom_id.bom_line_ids', readonly=False)
    operation_ids = fields.One2many(related='bom_id.operation_ids', readonly=False)
    lamina_tmpl_id = fields.Many2one('product.template', compute='compute_lattr')
    lamina_id = fields.Many2one('product.product', string='Lámina', compute='check_lamina_combination')
    new_combination_lamina = fields.Boolean('New lamina combination', compute='check_lamina_combination')
    specification_docs = fields.Many2many('ir.attachment', relation='m2m_ir_attachment_product_configurator_rel',
        column1='m2m_id', column2='attachment_id', string='Archivos ')
    origin = fields.Char('Origin', help='Technical field')
    change_possible = fields.Boolean('Change Possible')

    @api.onchange('parent_wiz_id')
    def _onchange_parent_wiz(self):
        if self.parent_wiz_id and self.parent_wiz_id.model_code == 'P':
            return {'domain': {'product_model': [('is_model', '=', True), ('default_code', 'not in', ['L', 'P'])]}}

    @api.constrains('product_model', 'ancho_lamina', 'largo_lamina')
    def _check_zero(self):
        for rec in self:
            if rec.model_code in ('P', 'Q', 'L') and (rec.ancho_lamina <= 0 or rec.largo_lamina <= 0):
                raise ValidationError('Must greater than zero!')

    @api.onchange('product_model', 'picking_type_id')
    def _create_model_bom_id(self):
        for rec in self.sudo():
            if rec.model_code in ('P', 'Q', 'E') and rec.picking_type_id and not rec.bom_id and not rec.product_id:
                bom_tmpl = self.env['mrp.bom'].search([
                    ('is_model', '=', True),
                    ('product_id', '=', rec.product_model.id),
                    ('picking_type_id', '=', rec.picking_type_id.id),
                ], limit=1)
                if bom_tmpl:
                    bom_tmpl = bom_tmpl.sudo()
                    if rec.bom_id and rec.picking_type_id != rec._origin.picking_type_id:
                        new_operations = []
                        for operation in bom_tmpl.operation_ids:
                            new_operations += [operation.sudo().copy(default={'bom_id': rec.bom_id.id}).id]
                        rec.operation_ids = [(6, 0, new_operations)]
                    else:
                        rec.bom_id = bom_tmpl[0].sudo().copy(default={'code': rec.id, 'is_model': False})

    @api.depends('product_id', 'calibre_search', 'papel_search', 'flauta_search', 'recub_search')
    def _compute_spec_values(self):
        for rec in self:
            rec.supplierinfos = [(5, 0)]
            rec.pricelist_items = [(5, 0)]
            if rec.product_id:
                rec.product_model = rec.product_id.product_model_id
                if not rec.calibre_search:
                    rec.calibre_search = rec.product_id.spec_calibre
                if not rec.papel_search:
                    rec.papel_search = rec.product_id.spec_papel
                if not rec.flauta_search:
                    rec.flauta_search = rec.product_id.spec_flauta
                if not rec.recub_search:
                    rec.recub_search = rec.product_id.spec_recub
                if not rec.origen:
                    rec.origen = rec.product_id.spec_origen or False
                rec.uom_input = rec.product_id.uom_size
                rec.ancho_input = rec.product_id.ancho_uom or 0
                rec.largo_input = rec.product_id.largo_uom or 0
                rec.alto_input = rec.product_id.alto_uom or 0
                rec.ancho_lamina = rec.product_id.spec_ancho_lamina or 0
                rec.largo_lamina = rec.product_id.spec_largo_lamina or 0
                rec.marca1 = rec.product_id.spec_marca1
                rec.marca2 = rec.product_id.spec_marca2
                rec.marca3 = rec.product_id.spec_marca3
                pricelist_items = rec.env['product.pricelist.item'].search([
                    '&',
                    '|', ('date_end', '>=', fields.Datetime.today()), ('date_end', '=', False),
                    '|', '|', '|',
                    ('applied_on', '=', '0_global'),
                    '&', ('applied_on', '=', '0_product_variant'), ('product_id', '=', rec.product_id.id),
                    '&', ('applied_on', '=', '1_product'), ('product_tmpl_id', '=', rec.product_tmpl_id.id),
                    '&', ('applied_on', '=', '2_product_category'), ('categ_id', '=', rec.product_id.categ_id.id),
                ])
                rec.pricelist_items = [(6, 0, pricelist_items.ids)]
                supplierinfos = self.env['product.supplierinfo'].search([
                    '&',
                    '|', ('date_end', '>=', fields.Datetime.today()), ('date_end', '=', False),
                    ('product_id', '=', rec.product_id.id)
                ])
                rec.supplierinfos = [(6, 0, supplierinfos.ids)]
                bom = self.env['mrp.bom'].search([('product_id', '=', rec.product_id.id)], limit=1)
                if bom:
                    rec.bom_id = bom
                    rec.bom_qty = bom.product_qty
                if rec.model_code == 'P':
                    rec.compute_lattr()
                    rec.check_lamina_combination()
            if rec.calibre_search:
                rec.calibre = rec.calibre_search.name
            if rec.papel_search:
                rec.papel = rec.papel_search.name
            if rec.flauta_search:
                rec.flauta = rec.flauta_search.name
            if rec.recub_search:
                rec.recub = rec.recub_search.name

    @api.onchange('uom_input', 'ancho_input', 'largo_input', 'alto_input')
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

    @api.onchange('product_style', 'uom_input', 'ancho', 'largo', 'alto', 'product_id')
    def _compute_dimensions(self):
        for rec in self:
            if not rec.product_id and all([rec.ancho > 0, rec.largo > 0]):
                if rec.product_style:
                    l = rec.largo
                    w = rec.ancho
                    h = rec.alto
                    rec.ancho_lamina = eval(rec.product_style.formula_ancho)
                    rec.largo_lamina = eval(rec.product_style.formula_largo)
                elif all([rec.ancho > 0, rec.largo > 0]):
                    rec.ancho_lamina = rec.ancho
                    rec.largo_lamina = rec.largo
            elif rec.product_id:
                rec.ancho_lamina = rec.product_id.spec_ancho_lamina
                rec.largo_lamina = rec.product_id.spec_largo_lamina

    @api.depends('product_id')
    def _compute_customer_product_id(self):
        for rec in self:
            if rec.product_id and rec.partner_id:
                rec.customer_product_id = self.env['product.customer.code'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('partner_id', '=', rec.partner_id.id)
                ], limit=1)
            elif rec.product_id:
                rec.customer_product_id = self.env['product.customer.code'].search([
                    ('product_id', '=', rec.product_id.id)
                ], limit=1)
                if rec.customer_product_id:
                    rec.partner_id = rec.customer_product_id.partner_id
            else:
                rec.customer_product_id = False

    @api.onchange('calibre', 'papel', 'flauta', 'recub', 'origen')
    def compute_lattr(self):
        for rec in self:
            rec.lamina_tmpl_id = False
            if all([rec.calibre, rec.papel, rec.flauta, rec.recub, rec.origen]):
                lamina_categ = self.env.ref('integreat_sale_product_configurator.lamina').id
                rec.lamina_tmpl_id = self.env['product.template'].search([
                    ('categ_id', '=', lamina_categ),
                    ('tmpl_calibre', '=', rec.calibre),
                    ('tmpl_papel', '=', rec.papel),
                    ('tmpl_flauta', '=', rec.flauta),
                    ('tmpl_recub', '=', rec.recub),
                    ('tmpl_origen', '=', rec.origen)
                ], limit=1)

    @api.onchange('lamina_tmpl_id', 'ancho_lamina', 'largo_lamina')
    def check_lamina_combination(self):
        for rec in self:
            # if rec.lamina_id:
            #     raise ValidationError('Change lamina???')
            rec.lamina_id = False
            rec.new_combination_lamina = True
            if rec.lamina_tmpl_id and all([rec.ancho_lamina, rec.largo_lamina]):
                ancho_value_id = rec.lamina_tmpl_id.attribute_line_ids[0].product_template_value_ids.filtered(
                    lambda v: v.product_attribute_value_id.name == str(rec.ancho_lamina))
                largo_value_id = rec.lamina_tmpl_id.attribute_line_ids[1].product_template_value_ids.filtered(
                    lambda v: v.product_attribute_value_id.name == str(rec.largo_lamina))
                if ancho_value_id and largo_value_id and rec.origen:
                    combination = [ancho_value_id.id, largo_value_id.id]
                    combination = self.env['product.template.attribute.value'].browse(combination)
                    is_combination_possible = rec.lamina_tmpl_id._is_combination_possible(combination)
                    if is_combination_possible:
                        lamina_id = rec.lamina_tmpl_id._get_variant_for_combination(combination)
                        if lamina_id:
                            rec.new_combination_lamina = False
                            rec.lamina_id = lamina_id
                            rec.marca1 = lamina_id.spec_marca1
                            rec.marca2 = lamina_id.spec_marca2
                            rec.marca3 = lamina_id.spec_marca3

    @api.onchange('product_model')
    def _get_prd_data(self):
        for rec in self:
            if rec.product_model:
                rec.prd_name = rec.product_model.name
                rec.prd_unspsc = rec.product_model.unspsc_code_id
                rec.sale_ok = rec.product_model.sale_ok
                rec.purchase_ok = rec.product_model.purchase_ok
                rec.image_1920 = rec.product_model.image_1920

    @api.model
    def create_assign_attribute_value(self, tmpl_attr_line, attrib):
        if attrib == 0:
            raise UserError('¡El valor 0 no está permitido!')

        aid = tmpl_attr_line.attribute_id

        value_id = self.env['product.attribute.value'].search([
            ('attribute_id', '=', aid.id),
            ('name', '=', str(attrib))
        ], limit=1)
        if not value_id:
            value_id = self.env['product.attribute.value'].sudo().create({
                'name': str(attrib),
                'attribute_id': aid.id
            })
        tmpl_attr_line.sudo().write({
            'value_ids': [(4, value_id.id)]
        })
        self.flush()

    def button_create_product(self):
        for rec in self.sudo():
            rec._compute_spec_values()
            rec.compute_lattr()
            rec.check_lamina_combination()
            lamina = rec.lamina_id
            product = rec.product_id
            if rec.new_combination_lamina and rec.ancho_lamina > 0 and rec.largo_lamina > 0:
                if not rec.lamina_tmpl_id:
                    # create new lamina template
                    lamina_model = self.env['product.template'].search([
                        ('default_code', '=', 'L'), ('is_model', '=', True)
                    ], limit=1)
                    calibre = rec.calibre_search
                    papel = rec.papel_search
                    flauta = rec.flauta_search
                    recub = rec.recub_search
                    defaults = {
                        'name': 'Lámina ' + calibre.name + papel.code + flauta.code + ' ' + recub.code + rec.origen,
                        'tmpl_calibre': calibre.name,
                        'tmpl_papel': papel.name,
                        'tmpl_flauta': flauta.name,
                        'tmpl_recub': recub.name,
                        'tmpl_origen': rec.origen,
                        'is_model': False,
                    }
                    reference_mask = 'L-' + calibre.code + '-' + papel.code + '-' + flauta.code + '-' \
                        + recub.code + '-' + rec.origen + '-[Ancho Lamina]x[Largo Lamina]'
                    lamina_tmpl_id = lamina_model.sudo().copy(default=defaults)
                    lamina_tmpl_id.sudo().write({
                        'reference_mask': reference_mask,
                        'product_model_id': rec.product_model.id,
                    })
                    rec._compute_spec_values()
                    rec.compute_lattr()
                ancho_tmpl_value_id = rec.lamina_tmpl_id.attribute_line_ids[0].product_template_value_ids.filtered(
                    lambda v: v.product_attribute_value_id.name == str(rec.ancho_lamina))
                if not ancho_tmpl_value_id:
                    self.create_assign_attribute_value(rec.lamina_tmpl_id.attribute_line_ids[0], rec.ancho_lamina)
                    ancho_tmpl_value_id = rec.lamina_tmpl_id.attribute_line_ids[0].product_template_value_ids.filtered(
                        lambda v: v.product_attribute_value_id.name == str(rec.ancho_lamina))
                largo_tmpl_value_id = rec.lamina_tmpl_id.attribute_line_ids[1].product_template_value_ids.filtered(
                    lambda v: v.product_attribute_value_id.name == str(rec.largo_lamina))
                if not largo_tmpl_value_id:
                    self.create_assign_attribute_value(rec.lamina_tmpl_id.attribute_line_ids[1], rec.largo_lamina)
                    largo_tmpl_value_id = rec.lamina_tmpl_id.attribute_line_ids[1].product_template_value_ids.filtered(
                        lambda v: v.product_attribute_value_id.name == str(rec.largo_lamina))
                lamina_combination = [ancho_tmpl_value_id.id, largo_tmpl_value_id.id]
                lamina_combination = self.env['product.template.attribute.value'].browse(lamina_combination)
                lamina = rec.lamina_tmpl_id.sudo()._create_product_variant(lamina_combination)
                valsl = {
                    'spec_calibre': rec.calibre,
                    'spec_papel': rec.papel,
                    'spec_flauta': rec.flauta,
                    'spec_recub': rec.recub,
                    'spec_origen': rec.origen,
                    'spec_ancho_lamina': rec.ancho_lamina,
                    'spec_largo_lamina': rec.largo_lamina,
                    'spec_marca1': rec.marca1,
                    'spec_marca2': rec.marca2,
                    'spec_marca3': rec.marca3,
                }
                lamina.sudo().write(valsl)
                if rec.model_code == 'L':
                    product = lamina
            valsp = {
                'spec_calibre': rec.calibre,
                'spec_papel': rec.papel,
                'spec_flauta': rec.flauta,
                'spec_recub': rec.recub,
                'spec_origen': rec.origen,
                'uom_size': rec.uom_input,
                'ancho_uom': rec.ancho_input,
                'largo_uom': rec.largo_input,
                'alto_uom': rec.alto_input,
                'spec_ancho': rec.ancho,
                'spec_largo': rec.largo,
                'spec_alto': rec.alto,
                'spec_ancho_lamina': rec.ancho_lamina,
                'spec_largo_lamina': rec.largo_lamina,
                'spec_marca1': rec.marca1,
                'spec_marca2': rec.marca2,
                'spec_marca3': rec.marca3,
                'unspsc_code_id': rec.prd_unspsc.id,
                'sale_ok': rec.sale_ok,
                'purchase_ok': rec.purchase_ok,
                'image_1920': rec.image_1920,
            }
            #product
            if not product:
                if rec.prd_name and rec.prd_name != rec.product_model.name:
                    name = rec.prd_name
                elif rec.product_name:
                    name = rec.product_name
                else:
                    name = rec.product_model.name

                product = rec.product_model.sudo().copy(default={
                    'name': name,
                    'is_model': False,
                    'product_model_id': rec.product_model.id
                })
                valsp.update({'default_code': rec.product_model.default_code + '-' + str(product.id).zfill(6)})
                product.sudo().write(valsp)
                rec.specification_docs.sudo().write({
                    'res_model': 'product.product',
                    'res_id': product.id
                })
                if rec.bom_id:
                    code = product.default_code or 'NUEVO'
                    bom_data = {
                        'product_tmpl_id': product.product_tmpl_id.id,
                        'product_id': product.id,
                        'code': code + ' (' + rec.picking_type_id.warehouse_id.code + ')',
                    }
                    if self._context.get('quotation_id', False):
                        quot_id = self._context.get('quotation_id')
                        quot = self.env['product.quotation.integreat'].browse(quot_id)
                        bom_data['code'] = quot.name
                        bom_data['type'] = 'quotation'
                        bom_data['quotation_id'] = quot_id
                        bom_data['bom_line_ids'] = [(0, 0, {
                            'product_id': rec.lamina_id.id,
                            'product_qty': 1,
                        })]
                        quot.sudo().write({'bom_id': rec.bom_id.id})
                    rec.sudo().bom_id.write(bom_data)
                else:
                    rec.sudo().product_id.write(valsp)
            # customer product data
            if rec.product_code:
                self.env['product.customer.code'].create({
                    'product_code': rec.product_code,
                    'product_name': rec.product_name,
                    'product_id': product.id,
                    'partner_id': rec.partner_id.id
                })
            # PRICES were saved on product_model => rewrite them
            if rec.supplierinfos_model:
                rec.supplierinfos_model.write({
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'product_id': product.id
                })
            if rec.pricelist_items_model:
                rec.pricelist_items_model.write({'product_id': product.id})
            if rec.parent_wiz_id and rec.parent_wiz_id.bom_id:
                if rec.model_code == 'L':
                    self.env.user.notify_warning(message='La lámina se ha creado, '
                        'pero no se ha agregado a la lista de materiales. '
                        'Debe seleccionarse durante el proceso de producción.', sticky=True)
                else:
                    bom_line = {
                        'bom_id': rec.parent_wiz_id.bom_id.id,
                        'product_id': product.id,
                        'product_qty': 1,
                    }
                    self.env['mrp.bom.line'].create(bom_line)
            rec.product_id = product
            rec.lamina_id = lamina
        if len(self.ids) > 1:
            self.unlink()
        elif self.origin == 'create':
            view_id = self.env.ref('product.product_normal_form_view').id
            return {
                'name': 'Producto',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'product.product',
                'res_id': self.product_id.id,
                'view_id': view_id,
                'target': 'current',
            }
        else:
            return self.wizard_reload()

    def button_add_component_line(self):
        view_id = self.env.ref('integreat_product_configurator.product_configurator_view_form').id
        context = {'default_parent_wiz_id': self.id, 'default_partner_id': self.partner_id and self.partner_id.id}
        name = 'Configurador de productos: Componente/Subproducto por PT'
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'product.configurator.integreat',
            'view_id': view_id,
            'target': 'new',
            'context': context,
        }

    def wizard_reload(self):
        view_id = self.env.ref('integreat_product_configurator.product_configurator_view_form').id
        action = {
            'name': 'Configurador de productos',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'product.configurator.integreat',
            'view_id': view_id,
            'target': 'new',
            'context': {}, # context,
        }
        if self.parent_wiz_id:
            action['res_id'] = self.parent_wiz_id.id
        else:
            action['res_id'] = self.id
        return action
