 Strathmore University SMS Module (su_sms)

## Overview

The Strathmore University SMS Module (`su_sms`) is a custom Odoo 19 application developed to manage the university’s internal and external SMS communications in a centralized, auditable, and cost-controlled manner.

The module replaces the legacy Laravel-based SMS portal and integrates directly into the Odoo ERP ecosystem. It supports messaging for students, staff, and departments while enforcing departmental billing, access control, and delivery tracking.

---

## Key Features

### Messaging
- Staff SMS: Filter recipients by Department, Gender, Job Status, and Category.
- Student SMS: Filter recipients by School, Program, Course, Academic Year, and Intake.
- Ad-hoc Messaging: CSV import and manual number entry for external or temporary recipients.
- Campaign-Based Workflow: Messages are managed as campaigns with draft, sending, and completed states.

### Financial Control
- Department-Based Billing: Every SMS is charged to a specific department cost center.
- Cost Estimation: Automatic calculation based on message length (160-character parts) and gateway rates.
- Expenditure Tracking: Real-time tracking of SMS usage per department.

### Integrations
- SMS Gateway: Direct REST integration with Africa’s Talking.
- Delivery Reports: Asynchronous callbacks for delivery status (Sent, Delivered, Failed).
- Blacklist Management: Automatic handling of opt-outs to ensure compliance.
- LDAP Connectivity Testing: Built-in tools to verify Active Directory connectivity.
- External Dataservice Testing: Health checks for student and staff dataservices.

---

## Technical Architecture

### System Requirements
- Odoo Version: 19.0
- Python: 3.10+
- Database: PostgreSQL 14+
- External Libraries:
  - requests
  - ldap3

### Module Structure
- `models/` – Core business logic (SMS, gateway, LDAP and dataservice tests)
- `views/` – XML definitions for forms, lists, dashboards, and menus
- `wizard/` – Transient models for composing messages and importing recipients
- `security/` – Security groups and access control rules
- `data/` – Default configuration data (SMS types, gateway templates)

---

## Installation

1. Copy the `su_sms` folder into your Odoo `custom_addons` directory.
2. Ensure the addons path is configured in `odoo.conf`.
3. Install Python dependencies inside the Odoo virtual environment:
   ```bash
   pip install requests ldap3

    Restart the Odoo service.

    Install the module from the Apps menu or via CLI:

    ./odoo-bin -i su_sms

Configuration
SMS Gateway Setup

    Navigate to SU SMS System → Configuration → Gateway Settings

    Create a new gateway configuration

    Enter Africa’s Talking credentials (Username, API Key, Sender ID)

    Select Sandbox or Production environment

    Use Test Connection to verify setup

LDAP & Dataservice Testing

    The module provides administrative test actions for:

        LDAP (Active Directory) connectivity

        Student dataservice availability

        Staff dataservice availability

    These tests are intended for administrators and diagnostics only.

Access Control

Security is enforced using Odoo groups:

    SMS User: View own campaigns and send limited ad-hoc SMS

    Department Admin: Send SMS to staff within their department

    Faculty Admin: Send SMS to students within their faculty

    System Administrator: Full access to configuration, logs, and system tests

Notes for Deployment

    Debug logging should be disabled in production to avoid performance degradation.

    LDAP and external service calls should not be executed synchronously in high-traffic user flows.

    This module is intended for internal university use.

Author & Metadata

Author: Francis Martin Agata
Department: ICT Department, Strathmore University
Version: 1.0.1
License: LGPL-3