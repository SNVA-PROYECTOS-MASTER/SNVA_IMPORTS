from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class PurchaseImport(models.Model):
    _name = 'purchase.import'
    _description = 'Purchase Import'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', readonly=True, copy=False, default='New')
    # Relación Many2many con órdenes de compra
    purchase_ids = fields.Many2many('purchase.order', string='Purchase Orders')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], string='Status', default='draft', tracking=True)
    #document_folder_id = fields.Many2one('documents.folder', string='Document Folder', readonly=True)

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
            parent_folder = self._get_year_folder(year)

            # subfolder = self.env['documents.folder'].create({
            #     'name': record.name,
            #     'parent_folder_id': parent_folder.id,
            # })

            # record.document_folder_id = subfolder.id
            record.state = 'confirmed'

    # @api.model
    # def create(self, vals):
    #     vals['document_folder_id'] = False  # por seguridad
    #     return super().create(vals)
    @api.model
    def create(self, vals):
        # Si no hay nombre asignado, generar el nombre con la secuencia
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.import') or 'IMP'

        # Asegura que document_folder_id sea None/False si no viene definido
        # vals['document_folder_id'] = vals.get('document_folder_id') or False

        return super().create(vals)
