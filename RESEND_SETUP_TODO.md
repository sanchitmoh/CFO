# 🚀 Resend Email Setup - Quick Start

## What You Need to Do

### 1. Get Resend API Key (2 minutes)

1. Go to https://resend.com/
2. Click **"Start Building"** (free, no credit card)
3. Sign up with email or GitHub
4. Verify your email
5. Go to https://resend.com/api-keys
6. Click **"Create API Key"**
7. Name: `AI CFO Development`
8. **Copy the key** (starts with `re_`)

⚠️ **Save it immediately** - you can only see it once!

---

### 2. Add Key to `.env` File

Open `backend/.env` and update this line:

**Find this:**
```bash
RESEND_API_KEY=
```

**Change to:**
```bash
RESEND_API_KEY=re_YourActualKeyGoesHere123456789
```

Also make sure this is set:
```bash
EMAIL_PROVIDER=resend
```

---

### 3. Test Email Delivery

Run the test script:

```bash
cd backend
python test_resend_email.py
```

**What it does:**
- ✅ Checks your configuration
- ✅ Sends 2 test emails (simple + alert format)
- ✅ Shows detailed success/error messages

**Expected output:**
```
✅ SUCCESS! Test email sent successfully!
📬 Check your inbox:
   Recipient: your@email.com
   Subject: ✅ Resend Test Email - AI CFO Platform
```

---

### 4. Check Your Email

Look for 2 emails:
1. **Simple test email** - "Resend is working!"
2. **Alert test email** - "Low Cash Balance Test Alert"

Check spam folder if you don't see them!

---

### 5. (Optional) Verify Your Domain

**For testing**: You can use `onboarding@resend.dev` as sender (no verification needed)

**For production**: Verify your own domain

1. Go to https://resend.com/domains
2. Click **"Add Domain"**
3. Enter: `yourdomain.com`
4. Add DNS records (TXT, MX, DKIM)
5. Wait 5-15 minutes
6. Update `.env`:
   ```bash
   EMAIL_FROM_ADDRESS=alerts@yourdomain.com
   ```

---

### 6. Deploy to Render

Once emails work locally, add to Render:

1. Go to Render dashboard
2. Your service → **Environment** tab
3. Add:
   - `EMAIL_PROVIDER` = `resend`
   - `RESEND_API_KEY` = `re_YourKey`
   - `EMAIL_FROM_ADDRESS` = `alerts@yourdomain.com`
4. Save (Render auto-redeploys)

---

### 7. Remove "Unavailable" Banner

Once emails work in production, update:

`frontend/app/(app)/settings/page.tsx`

Remove this section:
```tsx
{/* Temporary Deployment Issue Warning */}
<div className="mt-4 rounded-2xl p-3 flex items-start gap-2.5" style={{ background: "var(--warning-soft)", border: "1px solid var(--warning)44" }}>
  <AlertCircle size={16} style={{ color: "var(--warning)", flexShrink: 0, marginTop: 1 }} />
  <div>
    <p className="text-xs font-semibold" style={{ color: "var(--warning)" }}>Temporarily Unavailable</p>
    <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
      Email alerts are currently disabled due to deployment configuration issues...
    </p>
  </div>
</div>
```

---

## Troubleshooting

### "RESEND_API_KEY is not set"
- Check you added the key to `backend/.env`
- Make sure there's no space before or after the `=`
- Restart the backend if it's running

### "401 Unauthorized"
- Your API key is invalid
- Get a new key from https://resend.com/api-keys
- Make sure you copied the full key

### "403 Forbidden" or "Domain not verified"
- Use `onboarding@resend.dev` as sender for testing
- Or verify your domain at https://resend.com/domains

### Email not received
- Check spam folder
- Verify recipient email is correct
- Check Resend logs: https://resend.com/emails
- Try sending to a different email address

---

## Current Status

- [x] Resend integration added to backend
- [x] Configuration updated in .env
- [x] Test script created
- [ ] **YOU ARE HERE** → Get API key and test
- [ ] Verify emails work locally
- [ ] Deploy to Render
- [ ] Remove UI banner

---

## Quick Commands

```bash
# Test email locally
cd backend
python test_resend_email.py

# Check backend logs
cd backend
uvicorn main:app --reload

# Test via API
curl -X POST http://localhost:8000/api/v1/settings/alerts/test/email \
  -H "Authorization: Bearer YOUR_JWT"
```

---

## Need Help?

1. **Resend Docs**: https://resend.com/docs
2. **API Reference**: https://resend.com/docs/api-reference/emails/send-email
3. **Status Page**: https://status.resend.com/
4. **Backend Logs**: Check console for detailed errors
5. **Comprehensive Guide**: See `docs/RESEND_EMAIL_SETUP.md`

---

**Ready?** Get your API key and run the test! 🚀
