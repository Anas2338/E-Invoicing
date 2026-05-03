# Auto-Posting Feature - User Guide

## Overview

The Auto-Posting feature automatically posts validated invoices to FBR during your configured time windows, eliminating the need for manual posting while maintaining full control over when and how invoices are submitted.

## Features

### 1. Configurable Time Windows
- Set specific hours when auto-posting should be active (e.g., 9 AM - 6 PM)
- Supports midnight-spanning windows (e.g., 10 PM - 2 AM for night operations)
- Invoices are only posted during your configured hours

### 2. Daily Limits
- Set a maximum number of invoices to post per day (1-1000)
- Prevents accidental over-posting
- Limit resets at midnight PKT
- For midnight-spanning windows, the limit continues until the window ends

### 3. Environment Selection
- Choose between Sandbox (testing) and Production (live)
- Separate FBR credentials for each environment
- Production posting requires credential validation

### 4. Manual Override
- Post individual invoices manually at any time
- Works regardless of auto-posting settings or time window
- Counts toward daily limit

### 5. Emergency Pause
- Immediately disable auto-posting with one click
- Requires manual re-enable to resume
- Use when you need to stop posting immediately

### 6. Real-Time Monitoring
- View current status (active, paused, outside hours, etc.)
- See today's statistics (posted, failed, remaining)
- Track next check time
- 30-second auto-refresh

## Getting Started

### Step 1: Configure FBR Credentials

Before enabling auto-posting, ensure you have configured your FBR credentials:

1. Go to **Profile** → **FBR Integration Credentials**
2. Add your Sandbox token for testing
3. Add your Production token for live posting
4. Save credentials

### Step 2: Configure Auto-Posting Settings

1. Go to **Profile** → **Auto-Posting Settings**
2. Enable auto-posting toggle
3. Set your posting window:
   - **Start Time**: When posting should begin (e.g., 09:00)
   - **End Time**: When posting should stop (e.g., 18:00)
4. Select environment (Sandbox or Production)
5. Set daily limit (recommended: 100-500 for most users)
6. Click **Save Configuration**

### Step 3: Prepare Invoices

Auto-posting only works with invoices in **TRANSFERRED** status:

1. Create invoices in the system
2. Validate invoices (they move to VALIDATED status)
3. Transfer validated invoices (they move to TRANSFERRED status)
4. Auto-posting will pick them up during your configured hours

### Step 4: Monitor Activity

1. Go to **Invoices** → **History**
2. View the **Auto-Posting Status** widget
3. Check today's statistics
4. Monitor for any failures

## Time Window Examples

### Standard Business Hours
- **Start**: 09:00
- **End**: 18:00
- **Result**: Posts between 9 AM and 6 PM

### Night Shift Operations
- **Start**: 22:00
- **End**: 02:00
- **Result**: Posts from 10 PM until 2 AM next day

### Extended Hours
- **Start**: 08:00
- **End**: 20:00
- **Result**: Posts between 8 AM and 8 PM

## Daily Limit Behavior

### Normal Windows (Same Day)
- Limit resets at midnight PKT
- Example: 100 invoices per day from 9 AM - 6 PM

### Midnight-Spanning Windows
- Limit continues until window ends
- Example: Window 10 PM - 2 AM uses the same limit throughout
- New limit starts when the next window begins

## Manual Posting

### When to Use Manual Posting

- Need to post outside configured hours
- Auto-posting is disabled
- Need to post specific invoice immediately
- Daily limit reached but need to post anyway

### How to Manually Post

1. Go to **Invoices** → **History**
2. Find invoice with **TRANSFERRED** status
3. Click **Post to FBR** button
4. If daily limit reached, confirm override
5. Invoice posts immediately

## Emergency Pause

### When to Use

- Detected issue with invoices
- Need to stop posting immediately
- FBR system issues
- Need to review configuration

### How to Pause

1. Go to **Invoices** → **History**
2. Click **Emergency Pause** in Auto-Posting Status widget
3. Confirm action
4. Auto-posting stops within 5 minutes (next agent cycle)

### How to Resume

1. Go to **Profile** → **Auto-Posting Settings**
2. Enable auto-posting toggle
3. Save configuration
4. Auto-posting resumes at next scheduled time

## Troubleshooting

### Auto-Posting Not Working

**Check:**
1. Is auto-posting enabled in profile settings?
2. Are you within the configured time window?
3. Have you reached the daily limit?
4. Are there invoices in TRANSFERRED status?
5. Are FBR credentials configured correctly?

### Invoices Failing to Post

**Common Causes:**
1. Invalid FBR credentials
2. Invoice data validation errors
3. FBR API issues
4. Network connectivity problems

**Solution:**
1. Check invoice validation errors
2. Verify FBR credentials
3. Try manual posting to see specific error
4. Contact support if issue persists

### Daily Limit Reached Too Early

**Solutions:**
1. Increase daily limit in settings
2. Review which invoices are being posted
3. Consider splitting posting across multiple days
4. Use manual posting with override for urgent invoices

## Best Practices

### 1. Start with Sandbox
- Test auto-posting in Sandbox environment first
- Verify invoices post correctly
- Check FBR responses
- Switch to Production when confident

### 2. Set Appropriate Limits
- Start with conservative limits (50-100)
- Increase gradually based on volume
- Monitor failure rates
- Adjust as needed

### 3. Monitor Regularly
- Check status daily
- Review failure notifications
- Address issues promptly
- Keep FBR credentials up to date

### 4. Use Time Windows Wisely
- Align with business hours
- Avoid peak FBR system times if possible
- Consider time zones for international operations
- Test midnight-spanning windows carefully

### 5. Keep Credentials Secure
- Never share FBR tokens
- Rotate credentials periodically
- Use Production tokens only when ready
- Verify credentials after updates

## Security Notes

- All FBR credentials are encrypted at rest
- Auto-posting requires authentication
- Row-level data isolation enforced
- All posting attempts are logged
- Audit trail maintained for compliance

## Support

For issues or questions:
1. Check this guide first
2. Review error messages in invoice history
3. Check posting logs for details
4. Contact system administrator

## Limits and Quotas

- **Daily Limit Range**: 1-1000 invoices per day
- **Agent Check Interval**: Every 5 minutes
- **Max Invoices Per Cycle**: 10 per user
- **Retry Attempts**: 3 (with exponential backoff)
- **Network Timeout**: 30 seconds

## Changelog

### Version 1.0 (2026-05-02)
- Initial release
- Time-based auto-posting
- Daily limits
- Manual override
- Emergency pause
- Real-time monitoring
