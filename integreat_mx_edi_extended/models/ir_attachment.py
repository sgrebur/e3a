# -*- coding: utf-8 -*-

import mimetypes
from odoo import models, fields


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    # OVERRIDE
    # it is strange that xml files are considered as xml just when attachment is created by system user
    def _check_contents(self, values):
        values['mimetype'] = self._compute_mimetype(values)
        return values