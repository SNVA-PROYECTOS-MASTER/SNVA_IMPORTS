# wizards/purchase_import_wizard_line.py
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class PurchaseImportWizardLine(models.TransientModel):
    _name = 'purchase.import.wizard.line'
    _description = 'Wizard Line for Import Products'

    wizard_id = fields.Many2one('purchase.import.wizard', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_qty = fields.Float(string='Quantity', required=True)

    
    max_qty = fields.Float(string="Max Qty", compute="_compute_max_qty")

    @api.depends('product_id', 'wizard_id.purchase_order_id')
    def _compute_max_qty(self):
        for line in self:
            po = line.wizard_id.purchase_order_id
            pol = po.order_line.filtered(lambda l: l.product_id == line.product_id)
            line.max_qty = pol.product_qty if pol else 0.0

    @api.constrains('product_qty')
    def _check_product_qty(self):
        for line in self:
            if line.product_qty > line.max_qty:
                raise ValidationError("No puedes importar más de la cantidad en la orden de compra (%s unidades)." % line.max_qty)