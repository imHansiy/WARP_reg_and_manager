#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simplified fallback language system for warp_proxy_script.py compatibility
"""

# Simple fallback function for translation
def _(key, default=None):
    """Simple translation function - returns the key itself"""
    if default:
        return default
    return key

def get_language_manager():
    """Return None for compatibility"""
    return None
