# Strathmore University SMS Module (su_sms)

## Overview
The SU SMS Module is a custom Odoo 19 application designed to manage the university's internal and external SMS communications. It integrates directly with the Africa's Talking API to provide a cost-effective, reliable messaging service for students, staff, and faculty departments.

This system replaces the legacy Laravel-based SMS portal, centralizing communication within the university's ERP environment while maintaining strict departmental billing and audit trails.

## Key Features

### 1. Messaging Capabilities
- Staff SMS: Filter staff by Department, Gender, Job Status, and Category.
- Student SMS: Filter students by School, Program, Course, Academic Year, and Intake.
- Ad-Hoc Messaging: Support for CSV uploads and manual number entry for non-standard lists.
- Campaign Management: All messages are treated as campaigns with draft, sending, and completed states.

### 2. Financial Controls
- Departmental Billing: Every SMS is tracked against a specific department's cost center.
- Cost Calculation: Automated cost estimation based on character count (160-character parts) and gateway rates.
- Expenditure Tracking: Real-time logging of total credit usage per department.

### 3. Integration
- Gateway: Direct REST API integration with Africa's Talking.
- Delivery Reports: Asynchronous callback handling for delivery status updates (Sent, Delivered, Failed).
- Blacklist Management: Automated handling of opt-outs to ensure compliance.

## Technical Architecture

### System Requirements
- Platform: Odoo 19 (Enterprise/Community)
- Language: Python 3.10+
- Database: PostgreSQL 14+
- Dependencies: requests (Python library for API calls)

### Module Structure
- models/: Contains business logic for Campaigns, Gateway, and Departments.
- views/: XML definitions for Forms, Lists, Graphs, and Menus.
- wizard/: Transient models for composing messages and importing contacts.
- security/: Access control lists (ACLs) and Row-Level Security rules.
- data/: Default configuration data (SMS Types, Gateway Templates).

## Installation & Configuration

### 1. Deployment
1. Place the su_sms folder into the Odoo custom addons directory.
2. Update the Odoo configuration file (odoo.conf) to include the addons path.
3. Restart the Odoo service.
4. Install the module via the Apps menu or command line: ./odoo-bin -i su_sms

### 2. Gateway Setup
1. Navigate to SU SMS System > Configuration > Gateway Settings.
2. Create a new configuration record.
3. Enter the API Username, API Key, and Sender ID provided by Africa's Talking.
4. Set the environment to Production (or Sandbox for testing).
5. Click Test Connection to verify credentials.

## Access Control & Roles

The system uses standard Odoo security groups to manage access:

- Basic User: Can view own campaigns and send Ad-Hoc SMS.
- Department Admin: Can send messages to Staff within their department.
- Faculty Admin: Can send messages to Students within their faculty/school.
- System Admin: Full access to Configuration, Gateway settings, and all Department logs.

## Troubleshooting

### Connection Errors
If the system fails to send messages, check the Odoo server logs. Common issues include:
- Invalid Credentials: Verify API Key and Username in Gateway Settings.
- Network Restrictions: Ensure the server firewall allows outbound HTTPS (Port 443) traffic.

### Delivery Failures
- Invalid Numbers: Ensure phone numbers are in E.164 format (e.g., +2547...).
- Insufficient Balance: Check the gateway account balance.

## Support
Author: Francis Martine Nyabuto Agata
Department: ICT Department, Strathmore University
Version: 1.0.1
License: LGPL-3