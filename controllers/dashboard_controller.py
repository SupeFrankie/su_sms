# controllers/dashboard_controller.py

from odoo import http
from odoo.http import request
from datetime import datetime, timedelta
import json

class SMSDashboardController(http.Controller):
    
    @http.route('/sms/dashboard', type='http', auth='user', website=True)
    def sms_dashboard(self, **kwargs):
        """Render SMS dashboard with statistics"""
        
        user = request.env.user
        current_year = datetime.now().year
        
        # Base domain for current user
        domain = [('administrator_id.user_id', '=', user.id)]
        
        # Get all campaigns for current year
        year_start = datetime(current_year, 1, 1)
        year_campaigns = request.env['sms.campaign'].search(
            domain + [('create_date', '>=', year_start)]
        )
        
        # Calculate statistics
        total_sms_year = sum(year_campaigns.mapped('total_recipients'))
        total_cost_year = round(sum(year_campaigns.mapped('total_cost')), 2)
        total_sent = sum(year_campaigns.mapped('sent_count'))
        success_rate = round((total_sent / total_sms_year * 100) if total_sms_year > 0 else 0, 1)
        active_campaigns = request.env['sms.campaign'].search_count(
            domain + [('status', 'in', ['draft', 'scheduled', 'in_progress'])]
        )
        
        # Gender statistics
        gender_stats = self._get_gender_statistics(user)
        
        # Department statistics
        department_stats = self._get_department_statistics(user)
        
        # Monthly trend
        monthly_data = self._get_monthly_trend(user, current_year)
        
        # Recent campaigns
        recent_campaigns = self._get_recent_campaigns(user)
        
        values = {
            'user_name': user.name,
            'total_sms_year': total_sms_year,
            'total_cost_year': total_cost_year,
            'success_rate': success_rate,
            'active_campaigns': active_campaigns,
            
            'gender_stats': gender_stats['table'],
            'gender_labels': json.dumps(gender_stats['labels']),
            'gender_data': json.dumps(gender_stats['data']),
            
            'department_stats': department_stats['table'],
            'department_labels': json.dumps(department_stats['labels']),
            'department_data': json.dumps(department_stats['data']),
            
            'monthly_labels': json.dumps(monthly_data['labels']),
            'monthly_data': json.dumps(monthly_data['data']),
            
            'recent_campaigns': recent_campaigns,
        }
        
        return request.render('su_sms.sms_dashboard_template', values)
    
    def _get_gender_statistics(self, user):
        """Get SMS distribution by gender"""
        query = """
            SELECT 
                COALESCE(r.gender, 'Unknown') as gender,
                COUNT(*) as count
            FROM sms_recipient r
            JOIN sms_campaign c ON r.campaign_id = c.id
            JOIN sms_administrator a ON c.administrator_id = a.id
            WHERE a.user_id = %s
                AND EXTRACT(YEAR FROM c.create_date) = %s
            GROUP BY r.gender
            ORDER BY count DESC
        """
        
        request.env.cr.execute(query, (user.id, datetime.now().year))
        results = request.env.cr.fetchall()
        
        total = sum(r[1] for r in results)
        
        table = []
        labels = []
        data = []
        
        for gender, count in results:
            percentage = round(count / total * 100, 1) if total > 0 else 0
            table.append({
                'gender': gender.capitalize(),
                'count': count,
                'percentage': percentage
            })
            labels.append(gender.capitalize())
            data.append(count)
        
        return {'table': table, 'labels': labels, 'data': data}
    
    def _get_department_statistics(self, user):
        """Get SMS distribution by department"""
        query = """
            SELECT 
                COALESCE(r.department, 'Not Specified') as department,
                COUNT(*) as count,
                ROUND(SUM(r.cost), 2) as total_cost
            FROM sms_recipient r
            JOIN sms_campaign c ON r.campaign_id = c.id
            JOIN sms_administrator a ON c.administrator_id = a.id
            WHERE a.user_id = %s
                AND EXTRACT(YEAR FROM c.create_date) = %s
            GROUP BY r.department
            ORDER BY count DESC
            LIMIT 10
        """
        
        request.env.cr.execute(query, (user.id, datetime.now().year))
        results = request.env.cr.fetchall()
        
        table = []
        labels = []
        data = []
        
        for dept, count, cost in results:
            table.append({
                'department': dept,
                'count': count,
                'cost': round(cost, 2) if cost else 0
            })
            labels.append(dept if len(dept) <= 20 else dept[:17] + '...')
            data.append(count)
        
        return {'table': table, 'labels': labels, 'data': data}
    
    def _get_monthly_trend(self, user, year):
        """Get monthly SMS sending trend"""
        query = """
            SELECT 
                EXTRACT(MONTH FROM c.create_date) as month,
                COUNT(r.id) as count
            FROM sms_recipient r
            JOIN sms_campaign c ON r.campaign_id = c.id
            JOIN sms_administrator a ON c.administrator_id = a.id
            WHERE a.user_id = %s
                AND EXTRACT(YEAR FROM c.create_date) = %s
            GROUP BY EXTRACT(MONTH FROM c.create_date)
            ORDER BY month
        """
        
        request.env.cr.execute(query, (user.id, year))
        results = dict(request.env.cr.fetchall())
        
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        data = [results.get(float(i), 0) for i in range(1, 13)]
        
        return {'labels': months, 'data': data}
    
    def _get_recent_campaigns(self, user):
        """Get 10 most recent campaigns"""
        campaigns = request.env['sms.campaign'].search([
            ('administrator_id.user_id', '=', user.id)
        ], order='create_date desc', limit=10)
        
        result = []
        for campaign in campaigns:
            status_class_map = {
                'completed': 'success',
                'in_progress': 'info',
                'failed': 'danger',
                'cancelled': 'secondary',
                'draft': 'warning'
            }
            
            result.append({
                'name': campaign.name,
                'type': campaign.sms_type_id.name,
                'date': campaign.create_date.strftime('%Y-%m-%d %H:%M'),
                'recipients': campaign.total_recipients,
                'sent': campaign.sent_count,
                'cost': round(campaign.total_cost, 2),
                'status': campaign.status.replace('_', ' ').title(),
                'status_class': status_class_map.get(campaign.status, 'secondary')
            })
        
        return result