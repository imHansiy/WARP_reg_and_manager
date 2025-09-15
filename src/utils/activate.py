#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Quick account activation utility
This script activates the first healthy account found in the database.
"""

import sqlite3
import os
import sys

def activate_first_healthy_account():
    """Activate the first healthy account in the database"""
    # Get database path relative to script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    db_path = os.path.join(project_root, 'accounts.db')
    
    if not os.path.exists(db_path):
        print(f'❌ Database not found: {db_path}')
        return False
    
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get first healthy account
        cursor.execute('SELECT email FROM accounts WHERE health_status != "banned" LIMIT 1')
        result = cursor.fetchone()

        if result:
            email = result[0]
            # Set as active account
            cursor.execute('INSERT OR REPLACE INTO proxy_settings (key, value) VALUES ("active_account", ?)', (email,))
            conn.commit()
            print(f'✅ Account activated: {email}')
            return True
        else:
            print('❌ No healthy accounts found')
            return False
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    activate_first_healthy_account()