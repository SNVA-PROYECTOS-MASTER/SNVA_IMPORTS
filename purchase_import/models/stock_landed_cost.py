from odoo import models, fields

class StockLandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    import_id = fields.Many2one(
        'purchase.import',
        string='Importation'
    )
