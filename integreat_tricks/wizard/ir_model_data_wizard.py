# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class IntegreatModelWriteWizard(models.TransientModel):
    _name = 'ir.model.write.wizard'
    _description = 'Direct Write to Database'

    model = fields.Char(string='Model Name', required=True)
    field = fields.Char(string='Field', required=True)
    value = fields.Char(string='Value')
    condition = fields.Char(string='Condition')

    def button_write(self):
        query = """UPDATE %s SET %s=%s WHERE %s""" % (self.model, self.field, self.value, self.condition)
        self.env.cr.execute(query)


class IrModelDataWizard(models.TransientModel):
    _name = 'ir.model.data.wizard'
    _description = 'Create custom External Identifiers Wizard'

    model = fields.Char(string='Model Name', required=True)
    module = fields.Char(default='data', required=True)
    name_prefix = fields.Char(string='Prefix', required=True)
    name_field_1 = fields.Char(string='Unique Key Field 1', required=True)
    name_field_2 = fields.Char(string='Unique Key Field 2')
    name_field_3 = fields.Char(string='Unique Key Field 3')
    sub_field_1 = fields.Char(string='Unique Key Subfield 1')
    sub_field_2 = fields.Char(string='Unique Key Subfield 2')
    sub_field_3 = fields.Char(string='Unique Key Subfield 3')

    def button_process(self):
        model = self.env[self.model].search([])
        vals_list = []
        for rec in model:
            value = rec[self.name_field_1]
            if self.sub_field_1:
                value = value[self.sub_field_1]
            if value:
                name = self.name_prefix + '_' + (str(value).replace(' ', ''))
            else:
                continue
            if self.name_field_2:
                value = rec[self.name_field_2]
                if self.sub_field_2:
                    value = value[self.sub_field_2]
                if value:
                    name = name + '_' + (str(value).replace(' ', ''))
                else:
                    continue
            if self.name_field_3:
                value = rec[self.name_field_3]
                if self.sub_field_3:
                    value = value[self.sub_field_3]
                if value:
                    name = name + '_' + (str(value).replace(' ', ''))
                else:
                    continue
            exists = self.env['ir.model.data'].search([('module', '=', self.module), ('name', '=', name)])
            if not exists:
                vals = {
                    'name': name,
                    'model': self.model,
                    'module': self.module,
                    'res_id': rec.id
                }
                vals_list.append(vals)
        if vals_list:
            self.env['ir.model.data'].create(vals_list)