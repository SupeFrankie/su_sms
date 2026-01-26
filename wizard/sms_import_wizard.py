# wizard/sms_import_wizard.py


from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import csv
import io

class SMSImportWizard(models.TransientModel):
    _name = 'sms.import.wizard'
    _description = 'Import SMS Recipients'

    import_file = fields.Binary('Upload CSV File', attachment=False)
    file_name = fields.Char('File Name')
    
    # Context fields to know where to attach recipients
    campaign_id = fields.Many2one('sms.campaign', string="Campaign")
    mailing_list_id = fields.Many2one('sms.mailing.list', string="Mailing List")
    
    # Preview functionality
    preview_data = fields.Html("CSV Preview", readonly=True)
    valid_rows = fields.Integer("Valid Rows", readonly=True)
    has_error = fields.Boolean(default=False)
    error_message = fields.Text("Validation Errors", readonly=True)

    @api.onchange('import_file')
    def _onchange_file(self):
        if not self.import_file:
            return

        try:
            decoded_data = base64.b64decode(self.import_file)
            # Try to decode as utf-8, fallback to latin-1
            try:
                content = decoded_data.decode('utf-8')
            except UnicodeDecodeError:
                content = decoded_data.decode('latin-1')

            csv_file = io.StringIO(content)
            reader = csv.DictReader(csv_file)
            
            # Normalize headers (strip whitespace, lowercase)
            headers = [h.strip().lower() for h in reader.fieldnames] if reader.fieldnames else []
            required = ['first_name', 'last_name', 'phone_number']
            
            # Validation: Check headers
            missing = [col for col in required if col not in headers]
            if missing:
                self.has_error = True
                self.error_message = f"Missing required columns: {', '.join(missing)}"
                self.preview_data = ""
                return

            # Preview Logic
            valid_count = 0
            preview_html = "<table class='table table-sm table-striped'><thead><tr><th>First Name</th><th>Last Name</th><th>Phone</th><th>Status</th></tr></thead><tbody>"
            
            for index, row in enumerate(reader):
                if index >= 10:  # Only show first 10 for preview
                    break
                
                # Normalize row keys
                row = {k.strip().lower(): v for k, v in row.items()}
                
                f_name = row.get('first_name', '')
                l_name = row.get('last_name', '')
                phone = row.get('phone_number', '')
                
                status = "<span class='text-success'>✓ Valid</span>"
                if not phone:
                    status = "<span class='text-danger'>✗ Missing Phone</span>"
                elif not f_name and not l_name:
                    status = "<span class='text-warning'>⚠ Missing Name</span>"
                
                preview_html += f"<tr><td>{f_name}</td><td>{l_name}</td><td>{phone}</td><td>{status}</td></tr>"
                valid_count += 1

            preview_html += "</tbody></table>"
            
            self.preview_data = preview_html
            self.valid_rows = valid_count
            self.has_error = False
            self.error_message = ""

        except Exception as e:
            self.has_error = True
            self.error_message = f"Could not parse file: {str(e)}"

    def action_import(self):
        """Process the file and create records"""
        if self.has_error:
            raise UserError(_("Please fix the file errors before importing."))
        
        if not self.import_file:
            raise UserError(_("Please upload a CSV file first!"))

        decoded_data = base64.b64decode(self.import_file)
        try:
            content = decoded_data.decode('utf-8')
        except UnicodeDecodeError:
            content = decoded_data.decode('latin-1')
            
        csv_file = io.StringIO(content)
        reader = csv.DictReader(csv_file)
        
        count = 0
        skipped = 0
        Recipient = self.env['sms.recipient']
        Contact = self.env['sms.contact']
        Gateway = self.env['sms.gateway.configuration']

        for row in reader:
            # Normalize keys
            row = {k.strip().lower(): v for k, v in row.items()}
            
            first_name = row.get('first_name', '').strip()
            last_name = row.get('last_name', '').strip()
            name = f"{first_name} {last_name}".strip() or 'Unknown'
            phone = row.get('phone_number', '').strip()
            
            if not phone:
                skipped += 1
                continue
            
            # Normalize phone number
            try:
                phone = Gateway.normalize_phone_number(phone)
            except Exception as e:
                skipped += 1
                continue

            if self.campaign_id:
                # Add to campaign
                Recipient.create({
                    'campaign_id': self.campaign_id.id,
                    'name': name,
                    'phone_number': phone,
                    'status': 'pending'
                })
                count += 1
                
            elif self.mailing_list_id:
                # Add to mailing list
                contact = Contact.search([('mobile', '=', phone)], limit=1)
                if not contact:
                    contact = Contact.create({
                        'name': name,
                        'mobile': phone,
                        'contact_type': 'external',
                        'opt_in': True
                    })
                    count += 1
                
                # Link to mailing list
                if contact not in self.mailing_list_id.contact_ids:
                    self.mailing_list_id.contact_ids = [(4, contact.id)]
        
        # Show result
        message = f"Import completed!\n\n"
        message += f"✓ Imported: {count} contacts\n"
        if skipped > 0:
            message += f"⚠ Skipped: {skipped} invalid entries"
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Complete',
                'message': message,
                'type': 'success',
                'sticky': True,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_download_template(self):
        """Generate and download a sample CSV template"""
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write headers
        writer.writerow(['first_name', 'last_name', 'phone_number'])
        
        # Write sample data with various formats
        writer.writerow(['John', 'Doe', '+254712345678'])
        writer.writerow(['Jane', 'Smith', '0723456789'])
        writer.writerow(['Alice', 'Wanjiru', '734567890'])
        writer.writerow(['Bob', 'Ochieng', '+254745678901'])
        writer.writerow(['Carol', 'Akinyi', '0756789012'])
        
        # Get CSV content
        csv_content = output.getvalue()
        output.close()
        
        # Encode to base64
        csv_base64 = base64.b64encode(csv_content.encode('utf-8'))
        
        # Create attachment
        attachment = self.env['ir.attachment'].create({
            'name': 'sms_import_template.csv',
            'type': 'binary',
            'datas': csv_base64,
            'mimetype': 'text/csv',
            'public': False,
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }