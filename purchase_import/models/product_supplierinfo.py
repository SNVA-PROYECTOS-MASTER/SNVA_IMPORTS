from odoo import models, fields

class ProductSupplierinfo(models.Model):
    _inherit = 'product.supplierinfo'

    description_import = fields.Char(string="Descripción")