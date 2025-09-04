from odoo import models, api

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    # ---------- Helpers ----------
    def _pi__get_owner(self):
        # Usar root para evitar "Mi unidad" del usuario operativo
        return self.env.ref('base.user_root', raise_if_not_found=False) or self.env.user

    def _pi__get_parent_field(self):
        Doc = self.env['documents.document']
        # En algunas versiones es parent_id, en otras folder_id
        return 'parent_id' if 'parent_id' in Doc._fields else 'folder_id'

    def _pi__upsert_doc_for_attachment(self, att):
        """Crea o actualiza documents.document para un ir.attachment ligado a purchase.import.
        Soporta adjuntos subidos desde chatter, incluso si res_model/res_id se setean después."""
        # Sólo nos interesan adjuntos pegados a importaciones
        if att.res_model != 'purchase.import' or not att.res_id:
            return

        import_rec = self.env['purchase.import'].browse(att.res_id)
        folder = import_rec.document_folder_id
        if not import_rec or not folder:
            return

        Doc = self.env['documents.document']
        owner = self._pi__get_owner()
        parent_field = self._pi__get_parent_field()

        # ¿Ya existe documento para este attachment?
        doc = Doc.search([('attachment_id', '=', att.id)], limit=1)

        vals = {
            'name': att.name or att.datas_fname or f'Attachment {att.id}',
            'attachment_id': att.id,
            'company_id': import_rec.company_id.id,
            'owner_id': owner.id,
            'res_model': 'purchase.import',
            'res_id': import_rec.id,
        }

        # Community/folders: cuelga dentro de la carpeta (no workspace)
        # Si en tu instancia usas workspace, aquí podrías detectar y usar workspace_id.
        vals[parent_field] = folder.id

        if doc:
            # Actualiza ubicación / metadatos si cambiaron (p.ej. se subió antes de tener carpeta)
            update = {}
            for k, v in vals.items():
                if doc._fields.get(k) and getattr(doc, k, None) != v:
                    update[k] = v
            if update:
                doc.write(update)
        else:
            Doc.create(vals)

    # ---------- CREATE ----------
    @api.model_create_multi
    def create(self, vals_list):
        # Crea primero (batch-safe)
        attachments = super().create(vals_list)

        # Evitar interferir en instalación/upgrade (iconos de menú, etc.)
        if self.env.context.get('install_mode') or self.env.context.get('module'):
            return attachments

        # Post-proceso: intentar registrar documentos para los que ya traen res_model/res_id
        for att, vals in zip(attachments, vals_list):
            # Si desde el chatter aún no tenían res_model/res_id, write() se encargará luego
            if vals.get('res_model') == 'purchase.import' and vals.get('res_id'):
                self._pi__upsert_doc_for_attachment(att)

        return attachments

    # ---------- WRITE ----------
    def write(self, vals):
        # Detectar si ahora sí nos dieron res_model/res_id (caso típico chatter)
        needs_link = (
            ('res_model' in vals) or ('res_id' in vals)
            or ('res_model' in vals and 'res_id' in vals)
        )
        res = super().write(vals)

        # Evitar instalación/upgrade
        if self.env.context.get('install_mode') or self.env.context.get('module'):
            return res

        if needs_link:
            for att in self:
                self._pi__upsert_doc_for_attachment(att)

        return res
