# Strathmore University SMS Module (su_sms)

## Overview
The SU SMS Module is a custom Odoo 19 application designed to manage the university's internal and external SMS communications. It integrates directly with the Africa's Talking API to provide a cost-effective, reliable messaging service for students, staff, and faculty departments.

This system replaces the legacy Laravel-based SMS portal, centralizing communication within the university's ERP environment while maintaining strict departmental billing and audit trails.

## Key Features

### 1. Messaging Capabilities
- **Staff SMS**: Filter staff by Department, Gender, Job Status, and Category
- **Student SMS**: Filter students by School, Program, Course, Academic Year, and Intake
- **Ad-Hoc Messaging**: Support for CSV uploads for custom contact lists
- **Manual SMS**: Direct phone number entry for quick one-off messages
- **Campaign Management**: All messages tracked as campaigns with draft, sending, and completed states

### 2. Financial Controls
- **Departmental Billing**: Every SMS tracked against specific department cost centers
- **Cost Calculation**: Automated cost estimation based on character count and gateway rates
- **Expenditure Tracking**: Real-time logging of total credit usage per department
- **KFS5 Integration**: Export transaction data for financial system processing

### 3. Integration & Authentication
- **Gateway**: Direct REST API integration with Africa's Talking (sandbox and production)
- **LDAP Integration**: Active Directory authentication for staff access
- **Strathmore Dataservices**: Integration with university student/staff databases
- **Delivery Reports**: Asynchronous callback handling for delivery status updates
- **Blacklist Management**: Automated handling of opt-outs for compliance

### 4. Data Management
- **Contact Management**: Comprehensive contact database with opt-in/opt-out tracking
- **Mailing Lists**: Create and manage reusable contact groups
- **CSV Import**: Bulk import contacts from CSV files with validation
- **Recipient Tracking**: Individual recipient status monitoring per campaign
- **Blacklist System**: Prevent sending to opted-out or blocked numbers

### 5. Reporting & Analytics
- **Campaign Statistics**: Real-time tracking of sent, failed, and pending messages
- **Success Rate Monitoring**: Automated calculation of delivery success rates
- **Department Expenditure Reports**: Monthly and yearly spending analysis
- **Cost Analysis**: Detailed breakdown of SMS costs per campaign
- **Export Functionality**: Generate reports for external analysis

## Technical Architecture

### System Requirements
- **Platform**: Odoo 19 (Enterprise/Community)
- **Language**: Python 3.10+
- **Database**: PostgreSQL 14+
- **Operating System**: Ubuntu 24.04 LTS (recommended)
- **Memory**: Minimum 4GB RAM
- **Storage**: Minimum 10GB free space

### Python Dependencies
```bash
requests>=2.31.0
python-dotenv>=1.0.0
ldap3>=2.9.1
```

### Module Structure
```
su_sms/
├── __init__.py
├── __manifest__.py
├── controllers/
│   ├── __init__.py
│   ├── opt_controller.py          # Opt-in/opt-out web handlers
│   └── webhook_controller.py      # Africa's Talking webhooks
├── data/
│   ├── gateway_data.xml
│   ├── ir_cron.xml               # Scheduled jobs (disabled by default)
│   ├── sms_template_data.xml
│   └── sms_type_data.xml
├── models/
│   ├── __init__.py
│   ├── hr_department.py          # Department extensions for SMS
│   ├── mock_webservice.py        # LDAP & Dataservice adapter
│   ├── res_partner.py            # Partner extensions
│   ├── res_users.py              # User role management
│   ├── sms_administrator.py
│   ├── sms_blacklist.py
│   ├── sms_campaign.py
│   ├── sms_contact.py
│   ├── sms_dashboard.py
│   ├── sms_department.py
│   ├── sms_department_expenditure.py
│   ├── sms_gateway_config.py
│   ├── sms_mailing_list.py
│   ├── sms_recipient.py
│   ├── sms_staff_filter.py
│   ├── sms_student_filter.py
│   ├── sms_template.py
│   └── sms_type.py
├── security/
│   ├── ir.model.access.csv
│   └── security_groups.xml
├── views/
│   ├── sms_campaign_views.xml
│   ├── sms_contact_views.xml
│   ├── sms_gateway_views.xml
│   ├── sms_blacklist_views.xml
│   ├── sms_recipient_views.xml
│   ├── sms_staff_views.xml
│   ├── sms_student_views.xml
│   ├── hr_department_views.xml
│   ├── ldap_test_views.xml
│   ├── dataservice_test_views.xml
│   ├── menu_views.xml
│   └── opt_out_templates.xml
├── wizard/
│   ├── __init__.py
│   ├── sms_compose_wizard.py
│   ├── sms_compose_wizard_views.xml
│   ├── sms_import_wizard.py
│   └── sms_import_wizard_views.xml
└── static/
    └── description/
        ├── icon.png
        └── index.html
```

## Installation & Configuration

### 1. Pre-Installation Setup

#### Install Python Dependencies
```bash
# Install required Python packages
pip3 install requests --break-system-packages
pip3 install python-dotenv --break-system-packages
pip3 install ldap3 --break-system-packages
```

#### Create Environment Configuration
```bash
# Navigate to Odoo root directory
cd /path/to/odoo

# Create .env file
nano .env
```

Add the following configuration:
```bash
# Africa's Talking Configuration
AT_USERNAME=sandbox/your_app_name
AT_API_KEY=your_api_key_here
AT_SENDER_ID=your_sender_id
AT_ENVIRONMENT=sandbox/production

# SMS Configuration
SMS_MINIMUM_CREDIT=5000
SMS_ICTS_THRESHOLD=15000

# LDAP Configuration (Active Directory)
LDAP_HOST=123.34.567.789
LDAP_PORT=1234
LDAP_USERNAME=your_ldap_username
LDAP_PASSWORD=your_ldap_password
LDAP_BASE_DN=dc=your_ldap_base,dc=local
LDAP_TIMEOUT=5
LDAP_SSL=false
LDAP_TLS=false
SCHOOL_DOMAIN=school_domain
STUDENTS_DOMAIN=xxxxxxxxxxxxxx
LDAP_STAFF_TREE=OU=staff_tree ,DC=your_dc ,DC=your_dc
LDAP_STUDENT_TREE=ou=your_tree,dc=std,dc=xxxxxxx,dc=your_dc

# Strathmore Dataservices
STUDENT_DATASERVICE_URL=(students_link)
STAFF_DATASERVICE_URL=(staff_dataservice_link)
DATASERVICE_TIMEOUT=10
DATASERVICE_USE_MOCK=false
```

### 2. Module Deployment

#### Option A: Manual Installation
```bash
# Copy module to Odoo addons directory
cp -r su_sms /path/to/odoo/addons/

# Set proper permissions
chown -R odoo:odoo /path/to/odoo/addons/su_sms
chmod -R 755 /path/to/odoo/addons/su_sms

# Restart Odoo
sudo systemctl restart odoo

# Update module list
# Navigate to Apps > Update Apps List in Odoo
```

#### Option B: Command Line Installation
```bash
# Install module directly
./odoo-bin -c /etc/odoo/odoo.conf -i su_sms -d your_database --stop-after-init

# Restart Odoo service
sudo systemctl restart odoo
```

### 3. Gateway Configuration

#### Configure Africa's Talking Gateway
1. Navigate to **SU SMS System > Configuration > Gateway Settings**
2. Click **Create**
3. Fill in the following:
   - **Gateway Name**: Default Gateway
   - **Gateway Type**: Africa's Talking
   - **Username**: sandbox (or your production username)
   - **API Key**: Your Africa's Talking API key
   - **Sender ID**: STRATHU (or your approved sender ID)
   - **Test Phone Number**: +254712345678 (your test number)
4. Check **Is Default Gateway**
5. Click **Save**
6. Click **Test Connection** to verify setup

#### Alternative: Load from Environment
1. Click **Refresh from .env** button
2. Credentials will be loaded automatically from .env file
3. Click **Test Connection** to verify

### 4. LDAP & Dataservice Testing

#### Test LDAP Connection
1. Navigate to **SU SMS System > Configuration > Test LDAP Connection**
2. Click the menu item to execute test
3. Verify connection success message shows:
   - LDAP host and port
   - Base DN
   - Staff and student domains
   - Server information

#### Test All Services
1. Navigate to **SU SMS System > Configuration > Test All Services**
2. Click the menu item to execute comprehensive test
3. Verify all services show as ONLINE:
   - LDAP (Active Directory)
   - Student Dataservice
   - Staff Dataservice

### 5. User Access Configuration

#### Create SMS Administrators
1. Navigate to **Settings > Users & Companies > Users**
2. Select or create a user
3. Go to **SMS Access** tab
4. Set **SMS Department** (for billing)
5. Go to **Access Rights** tab
6. Under **SMS Marketing** section, assign appropriate role:
   - **SMS Basic User**: Ad-hoc and manual SMS only
   - **SMS Department Administrator**: Staff SMS for their department
   - **SMS Faculty Administrator**: Student SMS for their school
   - **SMS Administrator**: Full staff and student access
   - **SMS System Administrator**: All features + configuration

#### Department Setup
1. Navigate to **SU SMS System > Configuration > Departments**
2. For each department, configure:
   - **Short Name**: Department code
   - **Is School/Faculty**: Check if this is a school
   - **Chart Code**: SU (default)
   - **Account Number**: KFS5 account number
   - **Object Code**: KFS5 object code
   - **Department Administrator**: Assign user

## Usage Guide

### Sending Staff SMS

1. Navigate to **SU SMS System > Send SMS > Staff SMS**
2. Apply filters:
   - Department (if applicable)
   - Gender (All/Male/Female)
   - Category (Academic/Administrative)
   - Job Status (Full Time/Part Time/Intern)
3. Enter message content
4. Review character count and SMS parts
5. Click **Send SMS**

### Sending Student SMS

1. Navigate to **SU SMS System > Send SMS > Students SMS**
2. Apply filters:
   - School (if applicable)
   - Program
   - Course
   - Academic Year
   - Student Year
   - Intake
3. Select recipients:
   - Send to Students
   - Send to Fathers
   - Send to Mothers
4. Enter message content
5. Click **Send SMS**

### Ad-Hoc SMS (CSV Upload)

1. Navigate to **SU SMS System > Send SMS > Ad Hoc SMS**
2. Click **Create**
3. Enter campaign name
4. Click **Upload CSV**
5. Select CSV file with columns:
   - first_name
   - last_name
   - phone_number
6. Enter message content
7. Click **Send Now**

### Manual SMS (Direct Numbers)

1. Navigate to **SU SMS System > Send SMS > Manual SMS**
2. Click **Create**
3. Enter phone numbers (comma-separated):
   ```
   +254712345678, +254723456789, +254734567890
   ```
4. Enter message content
5. Click **Process Numbers**
6. Review recipients
7. Click **Send Now**

### Managing Campaigns

#### View All Campaigns
1. Navigate to **SU SMS System > Send SMS > All Campaigns**
2. Filter by:
   - Status (Draft/Completed/Failed)
   - SMS Type
   - Date range

#### Campaign Details
- **Recipients**: View all recipients and their delivery status
- **Statistics**: Total sent, failed, pending
- **Cost**: Total cost in KES
- **Success Rate**: Percentage of successful deliveries

### Blacklist Management

#### Add to Blacklist
1. Navigate to **SU SMS System > Configuration > Blacklist**
2. Click **Create**
3. Enter phone number
4. Select reason:
   - User Opt-out Request
   - Number Not Reachable
   - Spam Complaint
   - Administrator Action
5. Add notes (optional)
6. Click **Save**

#### User Self-Service Opt-Out
Users can opt-out via web link:
```
https://your-odoo-domain.com/sms/optout/+254712345678
```

Users can opt back in via:
```
https://your-odoo-domain.com/sms/optin/+254712345678
```

### Reports & Analytics

#### Department Expenditure Report
1. Navigate to **SU SMS System > Configuration > Departments**
2. View statistics:
   - SMS Credit Balance
   - SMS Sent This Month
   - SMS Cost This Month
3. Access detailed expenditure reports

#### Campaign Analysis
1. Navigate to **SU SMS System > Send SMS > All Campaigns**
2. Switch to **Graph** view for visual analysis
3. Switch to **Pivot** view for detailed breakdown
4. Group by SMS Type, Status, or Date

## Security & Permissions

### User Roles

#### SMS Basic User
- Create ad-hoc and manual SMS campaigns
- View own campaigns
- Cannot send to staff or students via filters

#### SMS Department Administrator
- All basic user permissions
- Send SMS to staff in their department
- View department statistics

#### SMS Faculty Administrator
- All basic user permissions
- Send SMS to students in their school/faculty
- View faculty statistics

#### SMS Administrator
- All department and faculty admin permissions
- Send to any staff or students
- View all campaigns
- Access reporting

#### SMS System Administrator
- Full system access
- Configure gateways
- Manage blacklist
- Configure departments
- Assign administrators
- Access all reports
- Test system connections

### Data Privacy

#### Student Identity Protection
- Numeric usernames (student IDs) are automatically identified as students
- Students cannot authenticate into the SMS system
- Student data is read-only from dataservices
- LDAP authentication explicitly blocks student accounts

#### Opt-Out Compliance
- Automatic blacklist checking before sending
- Public opt-out/opt-in web interface
- Blacklist reasons tracked for audit
- Failed deliveries logged with reasons

## Troubleshooting

### Connection Issues

#### LDAP Connection Failed
1. Verify LDAP credentials in .env file
2. Check LDAP_HOST and LDAP_PORT are correct
3. Ensure network connectivity to LDAP server
4. Test with: **Configuration > Test LDAP Connection**
5. Check Odoo logs: `/var/log/odoo/odoo-server.log`

#### Dataservice Connection Failed
1. Verify STUDENT_DATASERVICE_URL and STAFF_DATASERVICE_URL
2. Check network connectivity to server
3. Test with: **Configuration > Test All Services**
4. Enable mock data temporarily: `DATASERVICE_USE_MOCK=true`

#### Africa's Talking Gateway Failed
1. Verify AT_API_KEY is correct
2. Check AT_ENVIRONMENT (sandbox/production)
3. Ensure sender ID is approved
4. Test gateway: **Configuration > Gateway Settings > Test Connection**
5. Check account balance at Africa's Talking dashboard

### Sending Issues

#### No Recipients Found
**For Staff SMS:**
- Verify staff exist in dataservices
- Check department filter is not too restrictive
- Ensure LDAP connection is working
- Test with **Test All Services**

**For Student SMS:**
- Verify students exist in dataservices
- Check filters (school, year, program)
- Ensure dataservice URL is correct

#### Messages Stuck in Pending
1. Check gateway configuration
2. Verify API credentials are valid
3. Check Africa's Talking account balance
4. Review failed recipients for error messages
5. Check Odoo server logs for errors

#### High Failure Rate
1. Verify phone numbers are in E.164 format (+254...)
2. Check blacklist for blocked numbers
3. Review failure reasons in recipient details
4. Verify sender ID is approved
5. Check Africa's Talking account restrictions

### Import Issues

#### CSV Import Failed
1. Ensure CSV has required columns:
   - first_name
   - last_name
   - phone_number
2. Download template: **Import Recipients > Download Template**
3. Check file encoding is UTF-8
4. Verify no special characters in phone numbers
5. Remove empty rows

#### Invalid Phone Numbers
Supported formats:
- International: +254712345678
- Local (Kenya): 0712345678
- Without zero: 712345678
- With country code: 254712345678

### Performance Issues

#### Slow Campaign Creation
1. Reduce recipient count per campaign
2. Check database performance
3. Monitor server resources (CPU, RAM)
4. Optimize PostgreSQL configuration

#### Timeout on Large Imports
1. Split large CSV files into smaller batches
2. Increase Odoo timeout in configuration
3. Use mailing lists for recurring large groups

## Advanced Configuration

### KFS5 Financial Integration

#### Configure Export Path
Add to .env:
```bash
SMS_KFS5_DUMPS_PATH=/path/to/kfs5/dumps
SMS_KFS5_CREDIT_DEPT_ID=1
```

#### Export Format
The system generates three files:
- `sms_system_YYYYMMDD_HHMMpm.data` - Transaction data
- `sms_system_YYYYMMDD_HHMMpm.recon` - Reconciliation totals
- `sms_system_YYYYMMDD_HHMMpm.done` - Completion marker

#### Scheduled Export
Exports run automatically on the last day of each month at 23:30.
Manual export: Execute cron job `cron_export_to_kfs5`

### Custom System Parameters

Configure via **Settings > Technical > Parameters > System Parameters**:

- `sms.student_username_pattern`: Pattern for identifying students (default: numeric)
- `sms.webhook_secret`: Secret for webhook authentication
- `sms.low_credit_email_recipients`: Email list for low credit alerts
- `sms.kfs5_dumps_path`: Path for KFS5 export files
- `sms.kfs5_credit_dept_id`: Department ID for credit transactions

### Webhook Configuration

#### Setup Africa's Talking Webhooks
1. Log in to Africa's Talking dashboard
2. Navigate to SMS > Settings
3. Configure callback URLs:
   - **Delivery Reports**: `https://your-odoo-domain.com/sms/webhook/delivery`
   - **Incoming SMS**: `https://your-odoo-domain.com/sms/webhook/incoming`
4. Save configuration

#### Secure Webhooks (Optional)
Set webhook secret in system parameters:
```
sms.webhook_secret = your_random_secret_key
```

Update webhook_controller.py to validate:
```python
webhook_secret = self.env['ir.config_parameter'].sudo().get_param('sms.webhook_secret')
provided_secret = request.httprequest.headers.get('X-Webhook-Secret')
if webhook_secret and webhook_secret != provided_secret:
    return 'Unauthorized'
```

## Maintenance & Support

### Regular Maintenance Tasks

#### Daily
- Monitor campaign success rates
- Review failed messages
- Check gateway balance

#### Weekly
- Review blacklist additions
- Audit department expenditure
- Check system performance

#### Monthly
- Export KFS5 financial data
- Review overall statistics
- Clean old campaign data (if needed)

### Backup Recommendations

#### Database Backup
```bash
# Daily automated backup
pg_dump -U odoo -d your_database > /backups/odoo_$(date +%Y%m%d).sql
```

#### Configuration Backup
```bash
# Backup .env file
cp /path/to/odoo/.env /backups/.env.$(date +%Y%m%d)
```

### Log Monitoring

#### View Odoo Logs
```bash
# Real-time monitoring
tail -f /var/log/odoo/odoo-server.log

# Search for SMS errors
grep "SMS" /var/log/odoo/odoo-server.log | grep ERROR

# Search for LDAP issues
grep "LDAP" /var/log/odoo/odoo-server.log
```

### Updates & Upgrades

#### Module Updates
```bash
# Update module code
cp -r su_sms /path/to/odoo/addons/

# Upgrade module in database
./odoo-bin -c /etc/odoo/odoo.conf -u su_sms -d your_database --stop-after-init

# Restart Odoo
sudo systemctl restart odoo
```

## API Reference

### Phone Number Normalization

The system automatically normalizes phone numbers to E.164 format:

```python
# Input formats accepted:
0712345678          -> +254712345678
712345678           -> +254712345678
254712345678        -> +254712345678
+254712345678       -> +254712345678 (already normalized)

# International numbers:
+1234567890         -> +1234567890
+447123456789       -> +447123456789
```

### LDAP Integration

#### Authenticate User
```python
adapter = env['sms.webservice.adapter']
success, user_data = adapter.ldap_authenticate_user('username', 'password')
```

#### Get User Data
```python
adapter = env['sms.webservice.adapter']
user_data = adapter.ldap_get_user_data('username')
# Returns: {'username', 'first_name', 'last_name', 'email', 'is_student'}
```

### Dataservice Integration

#### Get Staff Data
```python
adapter = env['sms.webservice.adapter']
staff = adapter._get_staff(department_id=1, gender_id='1')
```

#### Get Student Data
```python
adapter = env['sms.webservice.adapter']
students = adapter._get_students(school_id=1, student_year='1')
```

## Version History

### Version 1.0.1 (Current)
- Initial production release
- LDAP integration for staff authentication
- Strathmore Dataservices integration
- Africa's Talking gateway support
- Campaign management system
- Blacklist management
- Department expenditure tracking
- CSV import functionality
- Webhook support for delivery reports
- Multi-level user access control
- KFS5 financial export (scheduled)

## License & Credits

### License
LGPL-3 (GNU Lesser General Public License v3.0)

### Author
**Francis Martine Nyabuto Agata**
- GitHub: SupeFrankie
- Department: ICT Department, Strathmore University

### Acknowledgments
- Strathmore University ICT Department
- Africa's Talking for SMS gateway services
- Odoo Community for framework support

### Support Contacts
- Technical Issues: ICT Department, Strathmore University

## Important Notes

### Production Deployment Checklist

Before deploying to production:

1. **Environment Configuration**
   - [ ] Update .env with production credentials
   - [ ] Set AT_ENVIRONMENT=production
   - [ ] Configure production API keys
   - [ ] Set proper LDAP credentials
   - [ ] Verify dataservice URLs

2. **Security**
   - [ ] Change default admin passwords
   - [ ] Configure webhook secrets
   - [ ] Set up SSL/HTTPS
   - [ ] Configure firewall rules
   - [ ] Enable database encryption

3. **Testing**
   - [ ] Test LDAP connection
   - [ ] Test dataservice connections
   - [ ] Test gateway with production credentials
   - [ ] Send test campaigns
   - [ ] Verify delivery reports
   - [ ] Test blacklist functionality

4. **Monitoring**
   - [ ] Set up log monitoring
   - [ ] Configure low credit alerts
   - [ ] Set up backup automation
   - [ ] Configure performance monitoring

5. **Documentation**
   - [ ] Document department configurations
   - [ ] Create user training materials
   - [ ] Document custom workflows
   - [ ] Update contact information

### Security Considerations

1. **Student Protection**: Students cannot authenticate into the system (enforced at LDAP layer)
2. **Department Isolation**: Users can only access their assigned departments
3. **Audit Trail**: All SMS sends are logged with timestamps and user information
4. **Blacklist Enforcement**: Automatic checking prevents sending to opted-out numbers
5. **Role-Based Access**: Strict permission system controls feature access

---

**End of Documentation**

For additional support or feature requests, please contact the ICT Department or submit an issue on the project repository.