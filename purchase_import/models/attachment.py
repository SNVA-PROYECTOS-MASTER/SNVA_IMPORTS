from odoo import models, api

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _get_documents_owner(self, company):
        """Devuelve un propietario 'neutral' para documentos.
        Ajusta a tus necesidades (p.ej., un usuario de servicio)."""
        admin = self.env.ref('base.user_admin', raise_if_not_found=False)
        return admin or self.env.user

    @api.model_create_multi
    def create(self, vals_list):
        # Crear primero TODOS los adjuntos (respetar batch)
        attachments = super().create(vals_list)

        # Si estamos en instalación/actualización de módulos, NO hagas nada extra.
        # (Aquí se crean iconos de menús, vistas, etc.)
        if self.env.context.get('install_mode') or self.env.context.get('module'):
            return attachments

        # Post-proceso sólo para adjuntos ligados a purchase.import
        # Ej: al adjuntar archivos desde el registro de importación.
        Doc = self.env['documents.document']
        for att, vals in zip(attachments, vals_list):
            if vals.get('res_model') == 'purchase.import' and vals.get('res_id'):
                import_rec = self.env['purchase.import'].browse(vals['res_id'])
                if import_rec and import_rec.document_folder_id:
                    # Odoo 18 usa workspace_id; pero si tu campo es folder (fallback),
                    # detecta el correcto de forma dinámica.
                    target_field = 'workspace_id' if 'workspace_id' in Doc._fields else 'folder_id'
                    owner = self._get_documents_owner(import_rec.company_id)
                    Doc.create({
                        'name': att.name,
                        'attachment_id': att.id,
                        target_field: import_rec.document_folder_id.id,
                        'company_id': import_rec.company_id.id,
                        'owner_id': owner.id,         # obligatorio en v18
                        'res_model': 'purchase.import',
                        'res_id': import_rec.id,
                    })
        return attachments
