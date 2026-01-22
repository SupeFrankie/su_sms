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

from dotenv import load_dotenv

load_dotenv()


# Import subpackages
from . import models
from . import wizard
from . import controllers

__all__ = ["models", "wizard", "controllers"]