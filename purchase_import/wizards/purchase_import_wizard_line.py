# wizards/purchase_import_wizard_line.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PurchaseImportWizardLine(models.TransientModel):
    _name = 'purchase.import.wizard.line'
    _description = 'Wizard Line for Import Products'

    wizard_id = fields.Many2one('purchase.import.wizard', ondelete='cascade')
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        domain="[('id', 'in', allowed_product_ids)]"
    )
    product_qty = fields.Float(string='Quantity', required=True)
    qty_received = fields.Float(string="Received" )
    product_uom = fields.Many2one('uom.uom',  string="Unit of Measure")
    price_unit = fields.Float(string="Unit Price")
    
    allowed_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_allowed_products',
        string='Allowed Products',
        store=False
    )
    max_qty = fields.Float(string="Max Qty", compute="_compute_max_qty")
    
    @api.depends('wizard_id.purchase_order_id')
    def _compute_allowed_products(self):
        for line in self:
            po = line.wizard_id.purchase_order_id
            if po:
                line.allowed_product_ids = po.order_line.mapped('product_id')
            else:
                line.allowed_product_ids = [(5, 0, 0)]

    @api.depends('product_id')
    def _compute_max_qty(self):
        for line in self:
            po = line.wizard_id.purchase_order_id
            pol = po.order_line.filtered(lambda l: l.product_id == line.product_id)
            if pol:
                total_ordered = sum(pol.mapped('product_qty'))
                total_received = sum(pol.mapped('qty_received'))
                line.max_qty = max(0.0, total_ordered - total_received)
            else:
                line.max_qty = 0.0


    @api.constrains('product_qty')
    def _check_product_qty(self):
        errors = []
        for line in self:
            if line.max_qty and line.product_qty > line.max_qty:
                errors.append(
                    f"• {line.product_id.display_name} — máximo permitido: {line.max_qty}, ingresado: {line.product_qty}"
                )
        if errors:
            raise ValidationError(
                "Algunos productos exceden la cantidad pendiente por recibir según la orden de compra:\n\n" +
                "\n".join(errors)
            )
