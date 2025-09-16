import sqlite3

conn = sqlite3.connect('accounts.db')
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
else:
    print('❌ No healthy accounts found')

conn.close()