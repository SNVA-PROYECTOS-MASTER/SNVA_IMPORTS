# wizards/purchase_import_wizard.py
from odoo import models, fields, api

class PurchaseImportWizard(models.TransientModel):
    _name = 'purchase.import.wizard'
    _description = 'Wizard to Select Products for Import'

    import_id = fields.Many2one('purchase.import', required=True)
    purchase_order_id = fields.Many2one('purchase.order', required=True,domain="[('id', 'in', allowed_purchase_ids)]")
    allowed_purchase_ids = fields.Many2many(
        'purchase.order',
        compute='_compute_allowed_purchase_orders'
    )
    line_ids = fields.One2many('purchase.import.wizard.line', 'wizard_id', string='Products')
    
    @api.depends('import_id')
    def _compute_allowed_purchase_orders(self):
        for wizard in self:
            wizard.allowed_purchase_ids = wizard.import_id.purchase_ids

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        active_model = self.env.context.get('active_model')

        if active_model == 'purchase.import':
            import_rec = self.env['purchase.import'].browse(active_id)
            res['import_id'] = import_rec.id
        elif active_model == 'purchase.order':
            purchase_rec = self.env['purchase.order'].browse(active_id)
            res['purchase_order_id'] = purchase_rec.id

        return res

    def action_add_products(self):
        for line in self.line_ids:
            self.env['purchase.import.line'].create({
                'import_id': self.import_id.id,
                'purchase_order_id': self.purchase_order_id.id,
                'product_id': line.product_id.id,
                'product_qty': line.product_qty
            })
            
    @api.onchange('purchase_order_id')
    def _onchange_purchase_order(self):
        if self.purchase_order_id:
            self.line_ids = [(5, 0, 0)]  # limpia las anteriores
            self.line_ids = [
                (0, 0, {
                    'product_id': line.product_id.id,
                    'product_qty': line.product_qty,
                })
                for line in self.purchase_order_id.order_line
            ]


