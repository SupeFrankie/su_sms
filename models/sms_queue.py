# models/sms_queue.py

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class SMSCampaign(models.Model):
    """Extended campaign with queue processing"""
    _inherit = 'sms.campaign'
    
    @api.model
    def cron_process_scheduled_campaigns(self):
        """
        Cron job to send scheduled campaigns
        PHP equivalent: Laravel queue worker processing
        Runs every 5 minutes
        """
        now = fields.Datetime.now()
        
        scheduled_campaigns = self.search([
            ('status', '=', 'scheduled'),
            ('schedule_date', '<=', now)
        ])
        
        for campaign in scheduled_campaigns:
            try:
                _logger.info(f'Processing scheduled campaign: {campaign.name}')
                campaign.status = 'in_progress'
                campaign._send_batch()
            except Exception as e:
                _logger.error(f'Failed to process campaign {campaign.id}: {str(e)}')
                campaign.write({
                    'status': 'failed',
                    'error_message': str(e)
                })
    
    @api.model
    def cron_retry_failed_recipients(self):
        """
        Retry failed recipients
        Runs daily
        """
        campaigns_with_failed = self.search([
            ('status', '=', 'completed'),
            ('failed_count', '>', 0)
        ])
        
        for campaign in campaigns_with_failed:
            failed_recipients = campaign.recipient_ids.filtered(
                lambda r: r.status == 'failed' and r.retry_count < 3
            )
            
            for recipient in failed_recipients:
                try:
                    success, result = campaign.gateway_id.send_sms(
                        recipient.phone_number, 
                        recipient.personalized_message or campaign.message
                    )
                    
                    if success:
                        recipient.write({
                            'status': 'sent',
                            'sent_date': fields.Datetime.now(),
                            'retry_count': recipient.retry_count + 1
                        })
                        campaign.sent_count += 1
                        campaign.failed_count -= 1
                    else:
                        recipient.retry_count += 1
                except Exception as e:
                    _logger.error(f'Retry failed for recipient {recipient.id}: {str(e)}')
                    recipient.retry_count += 1
    
    @api.model
    def cron_send_low_credit_email(self):
        """
        Send low credit warning email
        PHP equivalent: SendLowCreditEmail command
        Runs daily at 23:30
        """
        CreditManager = self.env['sms.credit.manager']
        balance_data = CreditManager.get_current_balance(force_refresh=True)
        
        minimum_balance = CreditManager._get_minimum_balance()
        
        if balance_data['balance'] <= minimum_balance:
            _logger.warning(f'Low SMS credit: KES {balance_data["balance"]:.2f}')
            
            # Get email recipients from config
            recipients_param = self.env['ir.config_parameter'].sudo().get_param(
                'sms.low_credit_email_recipients',
                default=''
            )
            
            if not recipients_param:
                _logger.warning('No low credit email recipients configured')
                return
            
            # Parse "Name - email@domain.com, Name2 - email2@domain.com"
            recipients = []
            for recipient_str in recipients_param.split(','):
                if '-' in recipient_str:
                    parts = recipient_str.split('-')
                    name = parts[0].strip()
                    email = parts[1].strip()
                    recipients.append({'name': name, 'email': email})
            
            # Send emails
            template = self.env.ref('su_sms.email_template_low_credit', raise_if_not_found=False)
            if template:
                for recipient in recipients:
                    template.with_context(
                        recipient_name=recipient['name'],
                        current_balance=balance_data['balance'],
                        minimum_balance=minimum_balance
                    ).send_mail(
                        self.id,
                        email_values={'email_to': recipient['email']},
                        force_send=True
                    )
                    
                _logger.info(f'Low credit email sent to {recipient["email"]}')
    
    @api.model
    def cron_export_to_kfs5(self):
        """
        Export SMS transactions to KFS5 financial system
        PHP equivalent: ExportTransactionsToKuali command
        Runs monthly on last day at 23:30
        """
        _logger.info('=== Starting KFS5 Export ===')
        
        # Get unprocessed campaigns
        campaigns = self.search([
            ('status', '=', 'completed'),
            ('kfs5_processed', '=', False),
            ('total_cost', '>', 0)
        ])
        
        if not campaigns:
            _logger.info('No campaigns to export')
            return
        
        # Get KFS5 configuration
        kfs5_path = self.env['ir.config_parameter'].sudo().get_param(
            'sms.kfs5_dumps_path',
            default='/tmp/kfs5'
        )
        
        credit_dept = self.env['hr.department'].search([
            ('id', '=', int(self.env['ir.config_parameter'].sudo().get_param(
                'sms.kfs5_credit_dept_id',
                default='1'
            )))
        ], limit=1)
        
        if not credit_dept:
            _logger.error('KFS5 credit department not configured')
            return
        
        import os
        from datetime import datetime
        
        # Create files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%p')
        base_filename = f'sms_system_{timestamp}'
        
        data_file_path = os.path.join(kfs5_path, f'{base_filename}.data')
        recon_file_path = os.path.join(kfs5_path, f'{base_filename}.recon')
        done_file_path = os.path.join(kfs5_path, f'{base_filename}.done')
        
        # Ensure directory exists
        os.makedirs(kfs5_path, exist_ok=True)
        
        # Generate data file content
        total_records = 0
        total_sum = 0.0
        
        with open(data_file_path, 'w') as data_file:
            for campaign in campaigns:
                dept = campaign.department_id
                if not dept or not dept.account_number or not dept.object_code:
                    _logger.warning(f'Campaign {campaign.id} missing department billing info')
                    continue
                
                fiscal_year = campaign.create_date.year
                fiscal_month = str(campaign.create_date.month).zfill(2)
                
                # Debit transaction (department)
                debit_line = self._format_kfs5_line(
                    fiscal_year=fiscal_year,
                    chart_code=dept.chart_code or 'SU',
                    account_number=dept.account_number,
                    object_code=dept.object_code,
                    fiscal_month=fiscal_month,
                    amount=campaign.total_cost,
                    debit_credit='D',
                    description=f'SMS bill for: {dept.short_name}'
                )
                
                # Credit transaction (credit department)
                credit_line = self._format_kfs5_line(
                    fiscal_year=fiscal_year,
                    chart_code=credit_dept.chart_code or 'SU',
                    account_number=credit_dept.account_number,
                    object_code=credit_dept.object_code,
                    fiscal_month=fiscal_month,
                    amount=campaign.total_cost,
                    debit_credit='C',
                    description=f'SMS bill for: {dept.short_name}'
                )
                
                data_file.write(credit_line + '\n')
                data_file.write(debit_line + '\n')
                
                total_records += 2
                total_sum += campaign.total_cost * 2
                
                # Mark as processed
                campaign.write({
                    'kfs5_processed': True,
                    'kfs5_processed_date': fields.Datetime.now()
                })
                
                _logger.info(f'Exported campaign {campaign.id} to KFS5')
        
        # Create recon file
        with open(recon_file_path, 'w') as recon_file:
            recon_file.write(f'c gl_entry_t {str(total_records).zfill(10)};\n')
            recon_file.write(f's trn_ldgr_entr_amt +{str(total_sum).zfill(21)};\n')
            recon_file.write('e 02;\n')
        
        # Create done file
        open(done_file_path, 'w').close()
        
        _logger.info(f'KFS5 export completed: {total_records} records, total: {total_sum}')
    
    def _format_kfs5_line(self, **kwargs):
        """Format a KFS5 transaction line"""
        from datetime import date
        
        # Extract parameters
        fiscal_year = str(kwargs.get('fiscal_year', date.today().year))
        chart_code = kwargs.get('chart_code', 'SU').ljust(2)[:2]
        account_number = kwargs.get('account_number', '').ljust(7)[:7]
        sub_account = ''.ljust(5)
        object_code = kwargs.get('object_code', '').ljust(4)[:4]
        sub_object = ''.ljust(3)
        balance_type = 'AC'.ljust(2)
        object_type = ''.ljust(2)
        fiscal_period = str(kwargs.get('fiscal_month', '01')).zfill(2)
        doc_type = 'AV'.ljust(4)
        system_origin = 'SM'.ljust(2)
        doc_number = ''.ljust(14)  # Would get from KFS5 API
        entry_sequence = ''.ljust(5)
        description = kwargs.get('description', 'SMS Transaction').ljust(40)[:40]
        amount = str(kwargs.get('amount', 0.0)).replace('.', '').zfill(21)
        debit_credit = kwargs.get('debit_credit', 'D')
        trans_date = date.today().strftime('%Y-%m-%d')
        org_doc_num = ''.ljust(10)
        project_code = ''.ljust(10)
        org_ref_id = ''.ljust(8)
        ref_doc_type = ''.ljust(4)
        ref_origin = ''.ljust(2)
        ref_doc_num = ''.ljust(14)
        reversal_date = ''.ljust(10)
        encumbrance = ''.ljust(1)
        
        # Concatenate all fields
        line = (
            fiscal_year + chart_code + account_number + sub_account +
            object_code + sub_object + balance_type + object_type +
            fiscal_period + doc_type + system_origin + doc_number +
            entry_sequence + description + amount + debit_credit +
            trans_date + org_doc_num + project_code + org_ref_id +
            ref_doc_type + ref_origin + ref_doc_num + reversal_date +
            encumbrance
        )
        
        return line


class SMSRecipient(models.Model):
    """Extended recipient with retry logic"""
    _inherit = 'sms.recipient'
    
    error_message = fields.Text(string='Error Message')
    retry_count = fields.Integer(string='Retry Count', default=0)