from odoo import models, api

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, vals):
        attachment = super().create(vals)

        if vals.get('res_model') == 'purchase.import' and vals.get('res_id'):
            record = self.env['purchase.import'].browse(vals['res_id'])
            if record and record.document_folder_id:
                self.env['documents.document'].create({
                    'name': attachment.name,
                    'attachment_id': attachment.id,
                    'folder_id': record.document_folder_id.id,
                    'owner_id': self.env.user.id,
                    'res_model': 'purchase.import',
                    'res_id': record.id,
                })

        return attachment


    
