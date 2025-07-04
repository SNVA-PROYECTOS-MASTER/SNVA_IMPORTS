from odoo import models, fields, api
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    import_id = fields.Many2one('purchase.import', string='Importación')
    
    def button_validate(self):
        # Ejecutar validaciones estándar primero
        res = super().button_validate()

        for picking in self:
            if picking.import_id:
                for move in picking.move_ids_without_package:
                    product = move.product_id
                    received_qty = move.quantity

                    if not received_qty:
                        continue

                    # 1. Actualizar líneas de la importación
                    import_lines = picking.import_id.import_line_ids.filtered(lambda l: l.product_id == product)
                    qty_to_assign = received_qty
                    for line in import_lines:
                        pendiente = line.product_qty - line.qty_received
                        if pendiente <= 0:
                            continue
                        agregar = min(pendiente, qty_to_assign)
                        line.qty_received += agregar
                        qty_to_assign -= agregar
                        if qty_to_assign <= 0:
                            break

                    # 2. Actualizar líneas de la orden de compra
                    for po in picking.import_id.purchase_ids:
                        po_lines = po.order_line.filtered(lambda l: l.product_id == product)
                        qty_to_assign_po = received_qty
                        for pol in po_lines:
                            pendiente_po = pol.product_qty - pol.qty_received
                            if pendiente_po <= 0:
                                continue
                            agregar_po = min(pendiente_po, qty_to_assign_po)
                            pol.qty_received += agregar_po
                            qty_to_assign_po -= agregar_po
                            if qty_to_assign_po <= 0:
                                break

        return res