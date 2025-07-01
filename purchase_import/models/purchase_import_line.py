# models/purchase_import_line.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PurchaseImportLine(models.Model):
    _name = 'purchase.import.line'
    _description = 'Purchase Import Line'

    import_id = fields.Many2one('purchase.import', string='Import', required=True, ondelete='cascade')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order',domain="[('id', 'in', allowed_purchase_ids)]")
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string='Quantity', required=True)
    price_unit = fields.Float(string='Unit Price')
    currency_id = fields.Many2one('res.currency', string="Currency", compute="_compute_currency", store=True)
    qty_received = fields.Float(string="Received" )
    allowed_purchase_ids = fields.Many2many(       
        'purchase.order',
        compute='_compute_allowed_purchase_orders',
        invisible=True,
        readonly=True,
        store=False
    )
    
    @api.depends('import_id')
    def _compute_allowed_purchase_orders(self):
        for wizard in self:
            wizard.allowed_purchase_ids = wizard.import_id.purchase_ids

    @api.depends('purchase_order_id.currency_id')
    def _compute_currency(self):
        for line in self:
            line.currency_id = line.purchase_order_id.currency_id if line.purchase_order_id else False

    @api.constrains('product_id', 'product_qty')
    def _check_line_not_empty(self):
        for line in self:
            if not line.product_id:
                raise ValidationError("Debes seleccionar un producto.")
            if line.product_qty <= 0:
                raise ValidationError("La cantidad debe ser mayor que cero.")