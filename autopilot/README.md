# AutoPilot README
## Deleqate AutoPilot — AI Pilot Agent

The AutoPilot is an autonomous AI agent that runs on your Windows laptop and handles Deleqate task assignments automatically.

---

## How It Works

```
Admin assigns order to AutoPilot pilot → Email sent to AutoPilot Gmail
→ Agent detects email → Fetches order from Deleqate → Downloads client files
→ Executes task (Gemini + Google Flow in Chrome) → QC check
→ Uploads deliverable → Marks order delivered → Emails admin report
```

---

## Setup (First Time)

### Step 1: Create the Gmail Account
1. Go to [accounts.google.com/signup](https://accounts.google.com/signup) in Incognito Chrome
2. Try these usernames in order until one works:
   - `pilot.deleqate@gmail.com`
   - `deleqate.pilot@gmail.com`
   - `autopilot.deleqate@gmail.com`
3. Subscribe to **Google One AI Premium** (₹1,950/month) for Gemini Advanced + Google Flow
4. Enable 2-Step Verification

### Step 2: Get Gmail App Password
1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select: App = **Mail**, Device = **Windows Computer**
3. Copy the 16-character code (it looks like: `xxxx xxxx xxxx xxxx`)

### Step 3: Enable Gmail IMAP
1. Open Gmail → Settings (gear) → See all settings
2. Forwarding and POP/IMAP tab → Enable IMAP
3. Save changes

### Step 4: Run the Installer
```
Double-click:  autopilot\INSTALL.bat
```

### Step 5: Configure the Agent
Edit `autopilot\.env`:
```
AUTOPILOT_EMAIL=pilot.deleqate@gmail.com      # Your actual Gmail
AUTOPILOT_APP_PASSWORD=xxxx xxxx xxxx xxxx    # From Step 2
AUTOPILOT_PILOT_PASSWORD=YourChosenPassword   # For Deleqate pilot account
AUTOPILOT_API_TOKEN=<generate below>          # Run: python -c "import secrets; print(secrets.token_hex(32))"
```

### Step 6: Create AutoPilot Pilot Account in Deleqate
1. Log in to Deleqate as admin
2. Create a new pilot account with:
   - Email: `pilot.deleqate@gmail.com` (same as AUTOPILOT_EMAIL)
   - Password: same as AUTOPILOT_PILOT_PASSWORD
3. Add `AUTOPILOT_API_TOKEN` to the main `Deleqate-main\.env` file

### Step 7: Sign Chrome into Google Account
1. The agent uses a separate Chrome profile
2. When you first run the agent, Chrome will open and ask you to sign in
3. Sign in as `pilot.deleqate@gmail.com`
4. You only need to do this once — the session persists

---

## Running the Agent

```bat
:: Start normally (runs forever, polls every 5 minutes)
autopilot\START_AUTOPILOT.bat

:: Or from command line:
python -m autopilot.agent

:: Test connectivity only:
python -m autopilot.agent --test

:: Process one task then stop:
python -m autopilot.agent --once

:: Debug mode (verbose logging):
python -m autopilot.agent --debug
```

---

## How Admin Assigns Tasks to AutoPilot

1. A client places an order
2. Admin opens the order in the admin dashboard
3. In the "Assign Pilot" dropdown, select **AutoPilot** (pilot.deleqate@gmail.com)
4. Click Assign → AutoPilot automatically receives an email notification
5. Within 5 minutes, the agent picks it up and starts processing

---

## Supported Task Types (Phase 1)

| Task Type | What It Does | Tools Used |
|-----------|-------------|-----------|
| `bg_cleanup` | Removes background from product photos | rembg (local AI) |
| `virtual_staging` | Adds furniture to empty rooms | Google Flow (browser) |
| `product_listing` | Generates Amazon/Flipkart listing copy | Gemini Advanced (browser) |
| `brand_starter_kit` | Creates brand guide with colors + fonts | Gemini Advanced (browser) |

---

## File Structure

```
autopilot/
├── agent.py                 # Main loop — start here
├── config.py                # Configuration loader
├── email_monitor.py         # Gmail IMAP watcher
├── deleqate_client.py       # Deleqate platform API client
├── browser_driver.py        # Playwright Chrome automation
├── task_queue.py            # SQLite task queue
├── executors/
│   ├── bg_cleanup.py        # Background removal
│   ├── virtual_staging.py   # Virtual staging (Google Flow)
│   └── product_listing.py   # Product listing (Gemini)
├── qc/
│   └── qc_engine.py         # QC: technical + Gemini vision
├── logs/
│   └── agent.log            # Agent activity log (rotated)
├── downloads/               # Downloaded client files (temp)
├── outputs/                 # Generated deliverables
├── queue.db                 # Task queue SQLite DB
├── .env                     # Your secrets (never commit!)
├── .env.template            # Template to copy from
├── INSTALL.bat              # Run once to set up
└── START_AUTOPILOT.bat      # Run to start the agent
```

---

## Monitoring

- **Admin dashboard** → shows AutoPilot online/offline status and last heartbeat
- **Log file** → `autopilot/logs/agent.log`
- **Email reports** → sent to `support@deleqate.com` on each task completion

---

## Troubleshooting

**Gmail login fails:**
→ Check AUTOPILOT_APP_PASSWORD is the App Password (not your login password)
→ Ensure IMAP is enabled in Gmail settings

**Deleqate login fails:**
→ Check AUTOPILOT_PILOT_PASSWORD matches the account created in admin dashboard
→ Ensure Deleqate server is running (check DELEQATE_BASE_URL)

**Google not signed in:**
→ When Chrome opens, manually sign in to pilot.deleqate@gmail.com
→ This persists for 30+ days in the Chrome profile

**Task not picked up:**
→ Check the admin email sent assignment notification (check ADMIN_GMAIL_APP_PASSWORD in main .env)
→ Manually check `autopilot/queue.db` to see task status
