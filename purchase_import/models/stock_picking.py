from odoo import models, fields, api
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    import_id = fields.Many2one('purchase.import', string='Importación')