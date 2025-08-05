from odoo import _,models, fields, api
from odoo.exceptions import UserError, ValidationError
from datetime import datetime

class PurchaseImport(models.Model):
    _name = 'purchase.import'
    _description = 'Purchase Import'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    document_folder_id = fields.Many2one(
        'documents.document',
        string='Document Folder',
        readonly=True,
        domain="[('id', '!=', False)]"
    )
    
    document_list = fields.One2many('documents.document',compute="_compute_document_list")
    
    
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

    tracking_number = fields.Many2one('res.partner', string="Trading Contact", domain="[('is_company', '=', False)]", tracking=True)

    notes = fields.Text(string="Internal Notes")

    import_line_ids = fields.One2many(
        'purchase.import.line',
        'import_id',
        string='Import Products'
    )
    forwarder = fields.Char(string="forwarder", tracking=True)
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
    
    trading_contact_id = fields.Many2one('res.partner', string="Trading Contact", domain="[('is_company', '=', False)]", tracking=True)
    
    picking_ids = fields.Many2many('stock.picking', compute="_compute_picking_ids", string="Receipts")
    
    picking_type_id = fields.Many2one(
        'stock.picking.type',
        string='Receipt Operation Type',
        domain=[('code', '=', 'incoming')],
        required=True,
        tracking=True
    )
    
    
    landed_cost_ids = fields.One2many(
        'stock.landed.cost', 'import_id',
        string="Landed Costs"
    )
    
    landed_cost_count = fields.Integer(
        string="Landed Cost Count",
        compute='_compute_landed_cost_count'
    )

    @api.depends('picking_ids')
    def _compute_landed_cost_count(self):
        for record in self: 
            landed_costs = self.env['stock.landed.cost'].search([
                ('picking_ids', 'in', record.picking_ids.ids)
            ])
        record.landed_cost_count = len(landed_costs)
    
    def action_view_landed_costs(self):
        self.ensure_one()
        # 1. Buscar recepciones vinculadas a esta importación
        related_pickings = self.env['stock.picking'].search([
            ('import_id', '=', self.id)
        ])
        
        # 2. Buscar landed costs que tengan esas recepciones
        landed_costs = self.env['stock.landed.cost'].search([
            ('picking_ids', 'in', related_pickings.ids)
        ])

        return {
            'type': 'ir.actions.act_window',
            'name': 'Landed Costs',
            'res_model': 'stock.landed.cost',
            'view_mode': 'list,form',
            'domain': [('id', 'in', landed_costs.ids)],
            'context': {'default_import_id': self.id}
        }
        
    @api.constrains('purchase_ids')
    def _check_unique_supplier(self):
        for record in self:
            supplier_ids = record.purchase_ids.mapped('partner_id.id')
            if supplier_ids and len(set(supplier_ids)) > 1:
                raise ValidationError("Todas las órdenes de compra deben tener el mismo proveedor para una importación.")
        
    @api.onchange('purchase_ids')
    def _onchange_purchase_ids_set_trading_contact(self):
        for record in self:
            if record.purchase_ids:
                # Tomar el proveedor de la primera OC vinculada
                first_po = record.purchase_ids[0]
                record.trading_contact_id = first_po.partner_id or False
            else:
                record.trading_contact_id = False
    
    def _get_document_list(self):
        
        folder_id  = self.document_folder_id
        documents = False
        if folder_id:
            documents = self.env['documents.document'].search([
                ('folder_id', '=' ,folder_id.id)
            ])
        return documents
        
    
    def _compute_document_list(self):
        for record in self:
            record.document_list = record._get_document_list()
            
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

    def action_confirm(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("Only draft imports can be confirmed.")

            if not record.import_line_ids:
                raise UserError("You must add at least one product before confirming the import.")

            if record.name == 'New':
                record.name = record.env['ir.sequence'].next_by_code('purchase.import') or 'IMP'

            # Preparar carpetas
            company = record.company_id
            documents = record.env['documents.document']
            year = str(datetime.now().year)

            # Carpeta raíz 'Importaciones' (única por empresa)
            root_folder = documents.search([
                ('name', '=', 'Importaciones'),
                ('type', '=', 'folder'),
                ('folder_id', '=', False),
                ('company_id', '=', company.id),
                ('owner_id', '=', 1)
            ], limit=1)
            if not root_folder:
                root_folder = documents.create({
                    'name': 'Importaciones',
                    'type': 'folder',
                    'company_id': company.id,
                    
                })

            # Carpeta del año actual
            year_folder = documents.search([
                ('name', '=', year),
                ('type', '=', 'folder'),
                ('folder_id', '=', root_folder.id),
                ('company_id', '=', company.id),
                
            ], limit=1)
            if not year_folder:
                year_folder = documents.create({
                    'name': year,
                    'type': 'folder',
                    'folder_id': root_folder.id,
                    'company_id': company.id,
                    'owner_id': self.env.user.id,
                })

            # Carpeta de la importación
            import_folder = documents.search([
                ('name', '=', record.name),
                ('type', '=', 'folder'),
                ('folder_id', '=', year_folder.id),
                ('company_id', '=', company.id),
            ], limit=1)
            if not import_folder:
                import_folder = documents.create({
                    'name': record.name,
                    'type': 'folder',
                    'folder_id': year_folder.id,
                    'company_id': company.id,
                    'owner_id': self.env.user.id,
                })

            # Asignar carpeta a la importación
            record.document_folder_id = import_folder.id

            # Validar líneas válidas
            valid_lines = record.import_line_ids.filtered(lambda l: l.product_id and l.product_qty > 0)
            if not valid_lines:
                raise UserError("No valid product lines to create a picking.")

            # Crear recepción
            picking_type = record.picking_type_id or record.env.ref('stock.picking_type_in', raise_if_not_found=False)
            if not picking_type:
                raise UserError("No valid incoming picking type found.")

            picking = record.env['stock.picking'].create({
                'partner_id': record.partner_id.id,
                'picking_type_id': picking_type.id,
                'location_id': picking_type.default_location_src_id.id,
                'location_dest_id': picking_type.default_location_dest_id.id,
                'origin': record.name,
                'company_id': company.id,
                'import_id': record.id,
            })

            for line in valid_lines:
                record.env['stock.move'].create({
                    'name': line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': picking.location_id.id,
                    'location_dest_id': picking.location_dest_id.id,
                    'picking_id': picking.id,
                    'company_id': company.id,
                })
            # Marcar como confirmado
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

    def action_open_document_folder(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Documentos',
            'res_model': 'documents.document',
            'view_mode': 'kanban,tree,form',
            'domain': [('folder_id', '=', self.document_folder_id.id)],
            'context': {'default_folder_id': self.document_folder_id.id},
        }
        
    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("No se puede eliminar líneas si la importación no está en estado Borrador.")
        return super().unlink()
    
    def action_set_to_draft(self):
        for record in self:
            if record.state != 'confirmed':
                continue

            # Buscar recepciones vinculadas
            pickings = record.picking_ids

            for picking in pickings:
                if picking.state == 'done':
                    raise UserError(_("You cannot reset to draft because a receipt has already been validated."))

            # Eliminar recepciones no validadas
            draft_pickings = pickings.filtered(lambda p: p.state != 'done')
            draft_pickings.unlink()

            # Revertir el estado
            record.state = 'draft'