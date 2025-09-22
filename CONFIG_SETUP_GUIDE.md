# Quick Setup Guide for config.yaml

## Configuration Structure

```yaml
mail:
  blocked_domains:       # Domains blocked by Warp.dev
  imap_settings:         # IMAP servers for different domains
  use_single_imap:       # Single IMAP server settings
```

## Main Sections

### 1. blocked_domains
Automatically managed list of domains blocked by Warp.dev:
```yaml
blocked_domains:
  - notboxletters.com
  - lettersboxmail.com
```
**Note**: Added automatically when domain blocking is detected

### 2. imap_settings
Mapping of email domains to IMAP servers:
```yaml
imap_settings:
  gmail.com: imap.gmail.com
  outlook.com: imap-mail.outlook.com
  notboxletters.com: imap.notletters.com
  # ... other domains
```

### 3. use_single_imap (optional)
To use a single IMAP server for all emails:
```yaml
use_single_imap:
  enable: false                # true - use single server
  imap_server: imap.gmail.com  # single IMAP server address
```

## Adding New Domain

### Automatic Addition
System automatically prompts to add IMAP server if domain not found:
```
⚠️ No IMAP server configured for domain: newdomain.com
💡 Please add 'newdomain.com: imap.newdomain.com' to config.yaml under mail.imap_settings
```

### Manual Addition
1. Open `config.yaml`
2. Add to `mail.imap_settings` section:
```yaml
  newdomain.com: imap.newdomain.com
```

## Popular IMAP Servers

| Provider | IMAP Server |
|----------|-------------|
| Gmail | imap.gmail.com |
| Outlook/Hotmail | imap-mail.outlook.com |
| Yahoo | imap.mail.yahoo.com |
| Mail.ru | imap.mail.ru |
| Rambler | imap.rambler.ru |
| GMX | imap.gmx.com |

## Password Requirements

### Gmail
- Requires **App Password**: https://myaccount.google.com/apppasswords
- Two-factor authentication must be enabled

### Outlook/Hotmail
- Requires **App Password**: https://account.live.com/proofs/AppPassword

### Yahoo
- Requires **App Password**: https://login.yahoo.com/account/security

## Troubleshooting

### AUTHENTICATIONFAILED Invalid credentials
1. Check email and password correctness
2. For Gmail/Outlook/Yahoo use App Password
3. Ensure IMAP server is correctly configured in config.yaml

### Domain not configured
1. Add domain to `mail.imap_settings`
2. Use format: `domain.com: imap.domain.com`

### Blocked domain
- Domains are automatically added to `blocked_domains` when blocking is detected
- Registration on blocked domains will be skipped

## Complete Configuration Example

```yaml
mail:
  blocked_domains:
    - spam-domain.com
    - blocked-provider.com
  
  imap_settings:
    gmail.com: imap.gmail.com
    outlook.com: imap-mail.outlook.com
    yahoo.com: imap.mail.yahoo.com
    mycompany.com: mail.mycompany.com
  
  use_single_imap:
    enable: false
    imap_server: imap.gmail.com
```

## Automatic Features

1. **Auto-blocking domains**: When "Email domain is not permitted" is detected, domain is automatically added to `blocked_domains`

2. **Successful registration cleanup**: Email addresses are automatically removed from `emails.txt` after successful registration

3. **Detailed diagnostics**: System provides detailed instructions for authentication errors