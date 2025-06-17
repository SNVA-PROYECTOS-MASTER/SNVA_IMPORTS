# models/purchase_import_line.py
from odoo import models, fields, api

class PurchaseImportLine(models.Model):
    _name = 'purchase.import.line'
    _description = 'Purchase Import Line'

    import_id = fields.Many2one('purchase.import', string='Import', required=True, ondelete='cascade')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string='Quantity', required=True)
    price_unit = fields.Float(string='Unit Price')
    currency_id = fields.Many2one('res.currency', string="Currency", compute="_compute_currency", store=True)

    @api.depends('purchase_order_id.currency_id')
    def _compute_currency(self):
        for line in self:
            line.currency_id = line.purchase_order_id.currency_id if line.purchase_order_id else False

