# -*- coding: utf-8 -*-
"""
SU SMS Module
==========================

This module provides comprehensive SMS management for university operations.

Author: Francis Martine Nyabuto Agata
Contact: SupeFrankie@github.com
"""

import os
import logging

_logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    
    possible_paths = [
        os.path.join(os.getcwd(), '.env'),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'),
        os.path.join(os.path.dirname(__file__), '.env'),
    ]
    
    env_loaded = False
    for env_path in possible_paths:
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
            _logger.info('SMS Module: Loaded .env from: %s', env_path)
            env_loaded = True
            break
    
    if not env_loaded:
        _logger.warning('SMS Module: No .env file found. Using database configuration only.')
            
except ImportError:
    _logger.warning('SMS Module: python-dotenv not installed. Using database configuration only.')

from . import models
from . import wizard
from . import controllers