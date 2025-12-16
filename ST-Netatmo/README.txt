🌉 Netatmo-SmartThings Bridge (Local Polling)
Allow the user to control their Netatmo thermostat on SmartThings with a customizable refresh rate (e.g., 5 minutes), enhanced mode control (Schedule, Away, Frost Guard), and visibility on the connection status.

This project replaces the official cloud integration (slow and unstable) with a reliable local connection.

🎯 Objectives
🚀 Speed: Updates every 5 minutes (vs. 6 hours for the official integration).

🛡️ Reliability: Local architecture (LAN) with automatic monitoring (Watchdog).

🌡️ Features: Full support for modes (Schedule, Away, Frost Guard) and setpoint adjustment.

❤️ Monitoring: Visual indicators of connection status (Hub ↔ Pi ↔ Netatmo).

🛠️ Hardware Requirements
A SmartThings Hub.

A server that runs 24/7 (Raspberry Pi, Synology NAS with Docker, or an older Linux/Windows PC).

Python 3.x installed on this server.

📝 Step 1: Netatmo API Configuration
We need to create a personal application to obtain access rights.

Log in to dev.netatmo.com with your usual Netatmo account.

Go to "My Apps" > "Create an App".

Name: SmartThings Bridge (or any name you prefer).

Description: Personal Integration.

Redirect URI: http://localhost (Important, even if we won't use it).

Save.

In your new app settings, copy and save:

Client ID

Client Secret

Token Generation (The Easy Way):

Scroll down to the "Token Generator" section.

Select scopes: read_thermostat, write_thermostat.

Click "Generate Token".

Copy the Refresh Token (it is the long string).

Note: You can ignore the Access Token as it expires quickly.

🖥️ Step 2: Server Installation (Raspberry Pi)
This Python script acts as a gateway between your Hub and Netatmo. It must run continuously.

1. Installation
Create a folder (e.g., netatmo_service) and copy the contents of the /netatmo_service folder from this repository into it.

2. Virtual Environment (Recommended)
Open a terminal in that folder:

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
3. Configuration
Rename the example file:

mv .env.example .env
nano .env
Fill in the fields with the data from Step 1:

CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_client_secret_here
REFRESH_TOKEN=your_refresh_token_here
(Optional) In app.py:

POLL_INTERVAL: Sets the refresh interval in seconds (default: 300s).

STALE_THRESHOLD: Timeout before reporting a connection error.

4. Manual Test
Start the server to verify everything works:

python3 app.py
If you see Running on http://0.0.0.0:5000 and ✅ Auto-update complete, you are good to go! (Stop with Ctrl+C).

5. Automatic Startup (Systemd)
To ensure the bridge starts automatically on boot:

Edit the provided netatmo.service file to match your actual file paths.

Install the service:

sudo cp netatmo.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable netatmo.service
sudo systemctl start netatmo.service
📱 Step 3: SmartThings Driver Installation
0. Prerequisites (SmartThings CLI)
You need the SmartThings CLI installed on your computer.

Open your terminal/command prompt.

Login to your account:

smartthings login
(Authorize via the browser window that opens).

Verify connection:

smartthings devices
1. Driver Configuration
Open the file driver/src/init.lua. Modify the following line with your Raspberry Pi's IP address:

local PI_IP = "192.168.1.XX" -- <--- Enter your Raspberry Pi IP address here
(You can also modify POLLING_INTERVAL here to change how often the Hub checks the Pi).

2. Installation via CLI
Open a terminal in the driver/ folder (where config.yaml is located).

A. Create a Channel

smartthings edge:channels:create
Name it (e.g., My Netatmo Channel).

Copy the Channel ID displayed (e.g., 5985...).

B. Enroll your Hub

smartthings edge:channels:enroll
Select your Hub.

Select the Channel you just created.

C. Package the Driver

smartthings edge:drivers:package .
Copy the Driver ID displayed (e.g., aafd...).

D. Assign Driver to Channel

smartthings edge:channels:assign
Select the Driver ID.

Select the Channel ID.

E. Install Driver on Hub

smartthings edge:drivers:install
Select the Driver.

Select the Hub.

3. Device Discovery
Open the SmartThings app on your phone.

Go to Devices > + (Add) > Scan.

The Netatmo Bridge device will appear.

Wait a few seconds... Your rooms (thermostats/valves) will be created automatically.

🩺 Troubleshooting & Indicators
The "Netatmo Bridge" device features two diagnostic indicators (Contact Sensors):

Hub ↔ Raspberry Pi:

✅ Closed: The Hub allows communication with the Python script.

❌ Open (Alert): The Hub cannot reach the Pi (Check IP address, or if app.py is running).

Pi ↔ Netatmo:

✅ Closed: The script is successfully communicating with Netatmo Cloud.

❌ Open (Alert): API error or Internet outage on the Raspberry Pi side.

Disclaimer: This is a personal project not affiliated with Netatmo or Samsung SmartThings. Use at your own risk.
