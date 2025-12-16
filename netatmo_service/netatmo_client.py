import socket
import requests
import requests.packages.urllib3.util.connection as urllib3_conn

def enforce_ipv4_only():
    urllib3_conn.allowed_gai_family = lambda: socket.AF_INET

enforce_ipv4_only()

HOMESDATA_URL = "https://api.netatmo.com/api/homesdata"
HOMESTATUS_URL = "https://api.netatmo.com/api/homestatus"  # <--- NOUVEAU
THERMOSTAT_URL = "https://api.netatmo.com/api/setroomthermpoint"
THERM_MODE_URL = "https://api.netatmo.com/api/setthermmode"

def get_homes_data(access_token):
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(HOMESDATA_URL, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()

# --- NOUVELLE FONCTION ---
def get_home_status(access_token, home_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"home_id": home_id}
    resp = requests.get(HOMESTATUS_URL, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()
# -------------------------

def set_thermostat_temperature(access_token, home_id, room_id, temperature):
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "home_id": home_id,
        "room_id": room_id,
        "mode": "manual",
        "temp": temperature
    }
    resp = requests.post(THERMOSTAT_URL, headers=headers, data=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()

def set_thermostat_mode(access_token, home_id, mode):
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "home_id": home_id,
        "mode": mode
    }
    resp = requests.post(THERM_MODE_URL, headers=headers, data=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()
