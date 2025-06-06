from odoo import models, fields

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Relación inversa con importaciones
    purchase_ids = fields.Many2many('purchase.import', string='Imports')
