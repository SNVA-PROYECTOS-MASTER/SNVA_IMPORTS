from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class PurchaseImport(models.Model):
    _name = 'purchase.import'
    _description = 'Purchase Import'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    # Relación Many2many con órdenes de compra
    purchase_ids = fields.Many2many('purchase.order', string='Purchase Orders',tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_production', 'In Production'),
        ('dispatched', 'Dispatched'),
        ('at_port', 'At Port'),
        ('in_customs', 'In Customs'),
        ('at_zf', 'At Zona Franca'),
        ('delivered', 'Delivered'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True)
    
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, string='Company', tracking=True)
    partner_id = fields.Many2one('res.partner', string='Supplier/Agent', tracking=True)
    
    transport_type = fields.Selection([
        ('maritime', 'Maritime'),
        ('air', 'Air'),
        ('land', 'Land'),
        ('courier', 'Courier')
    ], string="Transport Type", tracking=True)
    
    origin_country = fields.Char(string="Origin Country")
    port_of_loading = fields.Char(string="Port of Loading")
    port_of_discharge = fields.Char(string="Port of Discharge")
    departure_date = fields.Date(string="Departure Date")
    arrival_date = fields.Date(string="Estimated Arrival Date")
    incoterm_id = fields.Many2one('account.incoterms', string="Incoterm")
    #carrier_id = fields.Many2one('delivery.carrier', string="Carrier")

    tracking_number = fields.Char(string="Tracking Number")

    notes = fields.Text(string="Internal Notes")

    @api.model
    def _get_year_folder(self, year):
        # Buscar o crear carpeta "Imports/YYYY"
        folder_name = f'Imports/{year}'
        folder = self.env['documents.folder'].search([('name', '=', folder_name)], limit=1)
        if not folder:
            folder = self.env['documents.folder'].create({'name': folder_name})
        return folder

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("Only draft imports can be confirmed.")

            if record.name == 'New':
                record.name = self.env['ir.sequence'].next_by_code('purchase.import') or 'IMP'

            year = datetime.now().year
            #parent_folder = self._get_year_folder(year)
            record.state = 'confirmed'

    @api.model
    def create(self, vals):
        vals['name'] = 'New'
        return super().create(vals)

