import time
import threading
from flask import Flask, jsonify, request

from netatmo_auth import get_access_token
from netatmo_client import get_homes_data, get_home_status, set_thermostat_temperature, set_thermostat_mode
from state import update_state, get_state, is_data_stale

app = Flask(__name__)

POLL_INTERVAL = 300  # 5 minutes
STALE_THRESHOLD = 600 # 10 minutes

_forced_mode = None
_forced_mode_time = 0

def perform_update():
    global _forced_mode, _forced_mode_time
    try:
        token = get_access_token()

        # 1. Structure (Topology) - C'EST ICI QUE SE TROUVE LE MODE !
        topo_raw = get_homes_data(token)
        topo_body = topo_raw.get('body', topo_raw)
        if not topo_body or 'homes' not in topo_body:
            print("⚠️ Pas de données 'homes'")
            return False

        home_topo = topo_body['homes'][0]
        home_id = home_topo['id']
        home_name = home_topo.get('name', 'Maison')

        # 2. Status (Températures)
        status_raw = get_home_status(token, home_id)
        status_body = status_raw.get('body', status_raw)
        if not status_body or 'home' not in status_body:
             print("⚠️ Pas de données homestatus")
             return False

        home_status = status_body['home']

        # 3. Mapping Pièces
        rooms_status_map = {}
        for r in home_status.get('rooms', []):
            rooms_status_map[r['id']] = r

        # 4. Fusion Pièces
        final_rooms = []
        for room_topo in home_topo.get('rooms', []):
            r_id = room_topo['id']
            r_name = room_topo['name']
            r_status = rooms_status_map.get(r_id, {})
            temp_cur = r_status.get('therm_measured_temperature')
            temp_set = r_status.get('therm_setpoint_temperature')

            room_clean = {
                "id": r_id,
                "name": r_name,
                "temperature": temp_cur,
                "setpoint": temp_set,
            }
            final_rooms.append(room_clean)

        # 5. DÉTECTION DU MODE
        # 🔧 CORRECTION V15 : On regarde dans home_topo (TOPOLOGY) et pas home_status
        netatmo_mode = home_topo.get('therm_mode') 
        
        if not netatmo_mode: 
            netatmo_mode = home_topo.get('mode')
        
        if not netatmo_mode:
            # Fallback modules (au cas où)
            for mod in home_status.get('modules', []):
                if 'therm_setpoint_mode' in mod:
                    netatmo_mode = mod['therm_setpoint_mode']
                    break
        
        if not netatmo_mode: netatmo_mode = "schedule"

        print(f" > 📡 Mode lu chez Netatmo : {netatmo_mode}")

        # Gestion du mode optimiste (Latence API)
        final_mode = netatmo_mode
        if _forced_mode and (time.time() - _forced_mode_time < 60):
            print(f" > 🚀 Application du mode forcé (Latence) : {_forced_mode}")
            final_mode = _forced_mode
            if netatmo_mode == _forced_mode:
                _forced_mode = None
        else:
            _forced_mode = None 

        print(f" > ✅ Mode Final retenu : {final_mode}")

        # 6. Mise à jour État
        final_state = {
            "updated_at": int(time.time()),
            "homes": [{
                "id": home_id,
                "name": home_name,
                "thermostat": {
                    "id": home_id,
                    "mode": final_mode
                },
                "rooms": final_rooms
            }]
        }

        update_state(final_state)
        return True

    except Exception as e:
        print(f"❌ Update error: {e}")
        return False

def polling_loop():
    while True:
        print("🔄 Auto-refreshing Netatmo data...")
        if perform_update():
            pass 
        time.sleep(POLL_INTERVAL)

@app.route("/netatmo/state")
def netatmo_state():
    if is_data_stale(STALE_THRESHOLD):
        return jsonify({"error": "Data stale"}), 502
    return jsonify(get_state())

@app.route("/netatmo/debug")
def debug_raw():
    try:
        print("🕵️‍♂️ DEBUG RAW demandé")
        token = get_access_token()
        topo = get_homes_data(token)
        home_id = topo.get('body', {}).get('homes', [{}])[0].get('id')
        status = {}
        if home_id:
            status = get_home_status(token, home_id)
        return jsonify({
            "1_TOPOLOGY_RAW": topo,
            "2_STATUS_RAW": status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/netatmo/refresh", methods=['POST', 'GET'])
def force_refresh():
    print("⚡ Refresh manuel...")
    perform_update() 
    return jsonify(get_state())

@app.route("/netatmo/set_temp", methods=['POST'])
def set_temp():
    try:
        content = request.json
        home_id = content.get('home_id')
        room_id = content.get('room_id')
        temp = content.get('temp')
        print(f"🎮 Set Temp: {temp}°C")
        token = get_access_token()
        res = set_thermostat_temperature(token, home_id, room_id, temp)
        time.sleep(1)
        threading.Thread(target=perform_update).start()
        return jsonify({"status": "ok", "netatmo": res})
    except Exception as e:
        print(f"❌ Erreur Set Temp: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/netatmo/set_mode", methods=['POST'])
def set_mode():
    global _forced_mode, _forced_mode_time
    try:
        content = request.json
        home_id = content.get('home_id')
        mode = content.get('mode')
        print(f"🎮 Set Mode: {mode}")
        token = get_access_token()
        res = set_thermostat_mode(token, home_id, mode)
        _forced_mode = mode
        _forced_mode_time = time.time()
        threading.Thread(target=perform_update).start()
        return jsonify({"status": "ok", "netatmo": res})
    except Exception as e:
        print(f"❌ Erreur Set Mode: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    t = threading.Thread(target=polling_loop, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=5000)
