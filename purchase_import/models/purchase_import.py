from odoo import _,models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class PurchaseImport(models.Model):
    _name = 'purchase.import'
    _description = 'Purchase Import'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    # Relación Many2many con órdenes de compra
    purchase_ids = fields.Many2many('purchase.order', string='Purchase Orders',tracking=True, domain="['|', ('name', 'ilike', 'PI%'), ('name', 'ilike', 'PO%')]")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
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
    
    origin_country_id = fields.Many2one('res.country', string="Origin Country")
    port_of_loading = fields.Char(string="Port of Loading")
    port_of_discharge = fields.Char(string="Port of Discharge")
    departure_date = fields.Date(string="Departure Date")
    arrival_date = fields.Date(string="Estimated Arrival Date")
    incoterm_id = fields.Many2one('account.incoterms', string="Incoterm")
    #carrier_id = fields.Many2one('delivery.carrier', string="Carrier")

    tracking_number = fields.Char(string="Tracking Number")

    notes = fields.Text(string="Internal Notes")

    import_line_ids = fields.One2many(
        'purchase.import.line',
        'import_id',
        string='Import Products'
    )
    
    bl_number = fields.Char(string="BL Number", tracking=True)
    #Trading - contacto
    # Moneda de la importación
    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True
    )

    # TRM (valor numérico)
    trm_value = fields.Float(string="TRM", digits='Product Price', tracking=True)
    
    trading_contact_id = fields.Many2one(
        'res.partner',
        string="Trading Contact",
        domain="[('is_company', '=', False)]",  # opcional: solo personas
        tracking=True
    )
    
    picking_ids = fields.Many2many('stock.picking', compute="_compute_picking_ids", string="Receipts")
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Receipt Operation Type',
        domain=[('code', '=', 'incoming')],
        required=True,
        tracking=True
    )


    @api.depends('import_line_ids')
    def _compute_picking_ids(self):
        for record in self:
            pickings = self.env['stock.picking'].search([
                ('import_id', '=', record.id)
            ])
            record.picking_ids = pickings

            
    def action_view_pickings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Recepciones',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
            'context': {'default_import_id': self.id}
        }

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
    
    def action_open_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Select Products for Import',
            'res_model': 'purchase.import.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_import_id': self.id,
            }
        }
        

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', self.purchase_ids.ids)],
            'context': {'default_is_importation': True}
        }

    payment_ids = fields.Many2many(
        'account.payment',
        compute='_compute_payment_ids',
        string="Payments"
    )

    @api.depends('purchase_ids.invoice_ids.payment_ids')
    def _compute_payment_ids(self):
        for record in self:
            payments = self.env['account.payment']
            for po in record.purchase_ids:
                for invoice in po.invoice_ids:
                    payments |= invoice.payment_ids
            record.payment_ids = payments
    
    def action_create_reception(self):
        self.ensure_one()

        Picking = self.env['stock.picking']
        StockMove = self.env['stock.move']
        created_pickings = []

        for line in self.import_line_ids:
            if not line.product_id or not line.product_qty:
                continue

            partner = self.partner_id or (line.purchase_order_id and line.purchase_order_id.partner_id)
            if not partner:
                raise UserError(_("No partner defined for this reception."))

            # Usa el picking type predeterminado del usuario, o define uno por defecto en el modelo si aplica
            picking_type = self.env.ref('stock.picking_type_in', raise_if_not_found=False)
            if not picking_type:
                raise UserError(_("No default incoming picking type found."))

            picking = Picking.create({
                'partner_id': partner.id,
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'origin': self.name,
                'company_id': self.company_id.id,
                'import_id': self.id,
            })
            created_pickings.append(picking)

            StockMove.create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'picking_id': picking.id,
                'company_id': self.company_id.id,
            })

        if not created_pickings:
            raise UserError(_("No valid lines to create receptions."))

        return {
            'type': 'ir.actions.act_window',
            'name': 'Receipts',
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', [p.id for p in created_pickings])],
        }

