from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_ids = fields.Many2many('purchase.import', string='Imports')
    is_importation = fields.Boolean(string='Is Importation', default=False)
    transport_type = fields.Selection([
        ('maritime', 'Maritime'),
        ('air', 'Air'),
        ('land', 'Land'),
        ('courier', 'Courier')
    ], string="Transport Type")
    
    
    
    @api.constrains('purchase_ids')
    def _check_supplier_consistency_with_import(self):
        for order in self:
            for import_rec in order.purchase_ids:
                if import_rec.partner_id and order.partner_id != import_rec.partner_id:
                    raise ValidationError(
                        "No se puede asignar esta orden de compra a una importación con un proveedor diferente."
                    )

    
    def _create_picking(self):
        # Evitar recepciones automáticas si es importación
        importation_orders = self.filtered(lambda o: o.is_importation)
        normal_orders = self - importation_orders

        # Llama al método solo para las órdenes normales
        if normal_orders:
            return super(PurchaseOrder, normal_orders)._create_picking()

        # Para órdenes de importación, no crear nada
        return self.env['stock.picking']


    @api.model
    def create(self, vals):
        if not vals.get('name'):
            if not vals.get('is_importation'):
                # Solo asignar nombre si no es importación
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order') or '/'
            else:
                # Si es importación, nombre temporal
                vals['name'] = '/'
        return super().create(vals)

    def button_confirm(self):
        for order in self:
            if order.is_importation:
                if order.name in ['/', 'New']:
                    transport_type = order.transport_type or 'default'
                    sequence_code = f'purchase.order.import.{transport_type}'
                    sequence = self.env['ir.sequence'].search([('code', '=', sequence_code)], limit=1)
                    if not sequence:
                        sequence_code = 'purchase.order.import'
                    next_number = self.env['ir.sequence'].next_by_code(sequence_code)
                    if not next_number:
                        raise UserError("No se pudo generar el número de secuencia.")
                    order.name = next_number

        # Llamar a super() una sola vez después del loop
        res = super().button_confirm()

        # Cancelar recepciones automáticas si es importación
        for order in self.filtered(lambda o: o.is_importation):
            pickings = getattr(order, 'picking_ids', False)
            if pickings:
                pickings.filtered(lambda p: p.state in ['draft', 'waiting', 'confirmed']).action_cancel()
        return res


    def write(self, vals):
        for record in self:
            if 'is_importation' in vals:
                if record.state != 'draft' and not vals.get('is_importation', record.is_importation):
                    raise UserError("No puedes desmarcar '¿Es importación?' en una orden confirmada.")
        return super().write(vals)

    def action_view_purchase_imports(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Importaciones',
            'res_model': 'purchase.import',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', self.purchase_ids.ids)],
            'context': {'default_purchase_ids': self.id},
        }
        
    

