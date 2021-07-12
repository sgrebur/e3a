# coding: utf-8

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_mx_edi_leyenda = fields.Boolean(string="Leyenda Fiscal")
    l10n_mx_edi_leyenda_texto = fields.Text(string="Texto")
    l10n_mx_edi_leyenda_norma = fields.Char(string="Norma")
    l10n_mx_edi_leyenda_disposicion = fields.Char(string="Disposicion")
