# -*- coding: utf-8 -*-
"""
ICT Operations SMS Module
==========================

This module provides comprehensive SMS management for university operations.

Key Components:
- models: Database models (tables)
- views: User interface definitions
- wizard: Interactive SMS sending wizard
- controllers: Web endpoints for opt-in/out
- security: Access rights and permissions

Author: Francis Martine Nyabuto Agata
Contact: SupeFrankie@github.com
"""

import os
from dotenv import load_dotenv

# Force load the .env file from the Odoo root directory
load_dotenv('/home/francis/Desktop/odoo/.env')

from . import models
from . import controllers
from . import wizard