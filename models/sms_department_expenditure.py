# models/sms_department_expenditure.py

from odoo import models, fields, api, tools

class DepartmentExpenditure(models.Model):
    _name = 'sms.department.expenditure'
    _description = 'Department SMS Expenditure Report'
    _auto = False
    _rec_name = 'department_id'
    
    department_id = fields.Many2one(
        'hr.department',
        string='Department',
        readonly=True
    )
    
    department_name = fields.Char(
        string='Department Name',
        readonly=True
    )
    
    department_short_name = fields.Char(
        string='Short Name',
        readonly=True
    )
    
    chart_code = fields.Char(
        string='Chart Code',
        readonly=True
    )
    
    account_number = fields.Char(
        string='Account Number',
        readonly=True
    )
    
    object_code = fields.Char(
        string='Object Code',
        readonly=True
    )
    
    campaign_id = fields.Many2one(
        'sms.campaign',
        string='SMS Campaign',
        readonly=True
    )
    
    month_sent = fields.Char(
        string='Month Sent',
        readonly=True
    )
    
    year_sent = fields.Char(
        string='Year Sent',
        readonly=True
    )
    
    # ADD THESE TWO FIELDS:
    kfs5_processed = fields.Boolean(
        string='KFS5 Processed',
        readonly=True
    )
    
    kfs5_processed_date = fields.Datetime(
        string='KFS5 Process Date',
        readonly=True
    )
    
    credit_spent = fields.Float(
        string='Credit Spent (KES)',
        readonly=True,
        digits=(12, 2)
    )
    
    def init(self):
        """Create database view for department expenditure reporting"""
        tools.drop_view_if_exists(self.env.cr, self._table)
        
        # UPDATED SQL - Now includes kfs5_processed fields
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY d.id, sc.id) AS id,
                    d.id AS department_id,
                    d.name AS department_name,
                    d.short_name AS department_short_name,
                    d.chart_code,
                    d.account_number,
                    d.object_code,
                    sc.id AS campaign_id,
                    LPAD(EXTRACT(MONTH FROM sc.create_date)::text, 2, '0') AS month_sent,
                    EXTRACT(YEAR FROM sc.create_date)::text AS year_sent,
                    sc.kfs5_processed,
                    sc.kfs5_processed_date,
                    (
                        SELECT ROUND(COALESCE(SUM(sr.cost), 0)::numeric, 2)
                        FROM sms_recipient sr
                        WHERE sc.id = sr.campaign_id
                    ) AS credit_spent
                FROM
                    hr_department d
                    INNER JOIN res_users u ON d.id = u.department_id
                    INNER JOIN sms_campaign sc ON u.id = sc.administrator_id
                WHERE
                    sc.status = 'completed'
            )
        """ % self._table)