from odoo import models, fields, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    supplier_description = fields.Char(
        string="Descripción Proveedor",
        compute="_compute_supplier_description",
        store=False,
    )
    
    number_part = fields.Char(
        string="Number part",
        compute="_compute_number_part",
        store=False,
    )

    @api.depends('partner_id')
    def _compute_supplier_description(self):
        for line in self:
            # Previene errores si faltan datos
            if not line.product_id or not line.order_id or not line.order_id.partner_id:
                line.supplier_description = ''
                continue
            supplierinfo = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                ('partner_id', '=', line.order_id.partner_id.id)
            ], limit=1)
            line.supplier_description = supplierinfo.description_import if supplierinfo else ''
    
    @api.depends('partner_id')
    def _compute_number_part(self):
        for line in self:
            # Previene errores si faltan datos
            if not line.product_id or not line.order_id or not line.order_id.partner_id:
                line.number_part = ''
                continue
            number_part = self.env['product.supplierinfo'].search([
                ('product_tmpl_id', '=', line.product_id.product_tmpl_id.id),
                ('partner_id', '=', line.order_id.partner_id.id)
            ], limit=1)
            line.number_part = number_part.number_part if number_part else ''
