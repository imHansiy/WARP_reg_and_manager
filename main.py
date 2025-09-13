#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Warp Account Manager - Main Entry Point
This is the entry point for the application after restructuring into packages.
"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run the main application
from src.core.warp_account_manager import main

if __name__ == "__main__":
    main()