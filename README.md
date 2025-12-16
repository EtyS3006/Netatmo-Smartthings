# Netatmo-Smartthings
Allow the user to control their Netatmo thermostat on SmartThings with a customizable refresh rate (5 minutes for example), more suitable control of modes (away, frost protection), and visibility on the connection status.

SmartThings Netatmo Bridge
This project allows you to control Netatmo valves and thermostats within SmartThings with a fast refresh rate (5 minutes) and a reliable local connection, replacing the official integration (slow and unstable).

🎯 Objectives
Speed: Updates every 5 minutes (vs. 6 hours for the official integration).

Reliability: Local architecture (LAN) with automatic monitoring (Watchdog).

Features: Full support for modes (Scheduled, Away, Frost Protection) and setpoint adjustment.

Monitoring: Visual indicators of connection status (Hub ↔ Pi ↔ Netatmo).

🛠️ Hardware Requirements
A SmartThings Hub.

A server that is always on (Raspberry Pi, Synology NAS with Docker, or an older Linux/Windows PC).

Python 3.x installed on this server.

📝 Step 1: Netatmo Configuration (API)
We need to create a "dummy" application to obtain access rights.

Log in to dev.netatmo.com with your usual Netatmo account.

Go to "My Apps" > "Create an App".

Name: SmartThings Bridge (or other).

Description: Custom Integration.

Redirect URI: http://localhost (Important, even if we don't use it).

Confirm.

In the settings of the created application, carefully copy:

Client ID

Client Secret

Token Generation (Easy Method):

In the "Token Generator" section (at the bottom of your app's page).

Select the scopes: read_thermostat, write_thermostat.

Obtain the Refresh Token (key step 🔑)

Netatmo uses OAuth2.

The refresh token allows your server to function without user interaction.

🔁 Obtain an authorization code

In your browser, open this URL (adjusting the client_id):

https://api.netatmo.com/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri=http://localhost&scope=read_thermostat write_thermostat&state=secure_state

👉 You will be redirected to http://localhost/?code=XXXXX

📋 Copy the value code=

🔁 Exchange the code for tokens

Run this command (or via Postman/curl):

curl -X POST https://api.netatmo.com/oauth2/token

-d grant_type=authorization_code

-d client_id=CLIENT_ID

-d client_secret=CLIENT_SECRET

-d code=AUTHORIZATION_CODE

-d redirect_uri=http://localhost

✅ Expected response:

{ "access_token": "xxx",

"refresh_token": "yyy",

"expires_in": 10800

}

👉 Keep the refresh_token safe

🖥️ Step 2: Server Installation (Raspberry Pi)
This Python script acts as a gateway. It must run continuously.

1. Installing the files
Create a folder (e.g., netatmo_bridge) and copy the contents of the /server folder from this repository into it.

2. Virtual Environment (Recommended)

cd netatmo_bridge
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
3. Key Configuration
Rename the .env.example file to .env:

mv .env.example .env
nano .env
Fill in the following fields with the information retrieved in step 1:

CLIENT_ID=your_client_id_here
CLIENT_SECRET=your_secret_client_here
REFRESH_TOKEN=your_refresh_token_here

In app.py:
The POLL_INTERVAL line sets the refresh interval in seconds (requesting information from Netatmo).
The STALE_THRESHOLD line sets the timeout before reporting a connection error to the Netatmo servers.

4. Testing Manual
Start the server to verify:

python3 app.py
If you see "Running on http://0.0.0.0:5000" and "✅ Auto-update complete", you're good to go! (Stop with Ctrl+C).

5. Automatic Startup (Systemd Service)
To have the bridge start automatically if the Raspberry Pi restarts:

Edit the provided netatmo.service file to adjust the path (if necessary).

Copy and enable it:

sudo cp netatmo.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable netatmo.service
sudo systemctl start netatmo.service

📱 Step 3: Installing the SmartThings Driver
This is the software that installs on your SmartThings Hub. To install it, we need to create a private "Distribution Channel".

1. IP Configuration
Open the file driver/src/init.lua. Modify the following line with your Raspberry Pi's IP address:

local PI_IP = "192.168.1.XX" -- <--- Enter your local IP address here
2. Installation via CLI (Command Line)
Open a terminal in the driver/ folder (where the config.yaml file is located).

A. Create Your Personal Channel
If you have never developed a driver before, create a channel:

smartthings edge:channels:create
Give it a name (e.g., My Netatmo Channel).

Note the channel ID that is displayed (e.g., 5985...).

B. Enroll Your Hub in the Channel
You need to allow your Hub to download from this channel:

smartthings edge:channels:enroll
Select your Hub from the list.

Select the channel you just created.

C. Package the Driver
This compiles the code and prepares the driver.

smartthings edge:drivers:package .
Note the Driver ID that is displayed (e.g., aafd...).

D. Assign the Driver to the Channel
We put the package in the delivery truck:
