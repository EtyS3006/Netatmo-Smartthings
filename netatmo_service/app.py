import time
import threading
from flask import Flask, jsonify, request

from netatmo_auth import get_access_token
from netatmo_client import get_homes_data, get_home_status, set_thermostat_temperature, set_thermostat_mode
from state import update_state, get_state, is_data_stale # <-- On importe la nouvelle fonction

app = Flask(__name__)

POLL_INTERVAL = 300  # 5 minutes
STALE_THRESHOLD = 600 # 10 minutes (Si pas de maj après 2 cycles, on déclare l'erreur)

def perform_update():
    """Récupère Topologie + Status et fusionne le tout"""
    try:
        token = get_access_token()

        # 1. Récupération de la STRUCTURE
        topo_raw = get_homes_data(token)
        topo_body = topo_raw.get('body', topo_raw)

        if not topo_body or 'homes' not in topo_body:
            print("⚠️ Pas de données 'homes' dans homesdata")
            return False

        home_topo = topo_body['homes'][0]
        home_id = home_topo['id']
        home_name = home_topo.get('name', 'Maison')

        # 2. Récupération des VALEURS
        status_raw = get_home_status(token, home_id)
        status_body = status_raw.get('body', status_raw)

        if not status_body or 'home' not in status_body:
             print("⚠️ Pas de données dans homestatus")
             return False

        home_status = status_body['home']

        # 3. Mapping
        rooms_status_map = {}
        for r in home_status.get('rooms', []):
            rooms_status_map[r['id']] = r

        # 4. Fusion
        final_rooms = []
        print("\n--- 🕵️ VERITÉ VENUE DE NETATMO (FUSION) ---")

        for room_topo in home_topo.get('rooms', []):
            r_id = room_topo['id']
            r_name = room_topo['name']
            r_status = rooms_status_map.get(r_id, {})
            temp_cur = r_status.get('therm_measured_temperature')
            temp_set = r_status.get('therm_setpoint_temperature')

            print(f" > Pièce {r_name} ({r_id}) : Mesure={temp_cur}°C / Consigne={temp_set}°C")

            room_clean = {
                "id": r_id,
                "name": r_name,
                "temperature": temp_cur,
                "setpoint": temp_set,
            }
            final_rooms.append(room_clean)

        # Mode Global
        global_mode = "schedule"
        for mod in home_status.get('modules', []):
            if 'therm_setpoint_mode' in mod:
                global_mode = mod['therm_setpoint_mode']
                break

        print(f" > Mode Global Maison : {global_mode}")
        print("------------------------------------------\n")

        # 5. Mise à jour de l'état global
        final_state = {
            "updated_at": int(time.time()),
            "homes": [{
                "id": home_id,
                "name": home_name,
                "thermostat": {
                    "id": home_id,
                    "mode": global_mode
                },
                "rooms": final_rooms
            }]
        }

        update_state(final_state) # <-- Ceci mettra à jour le timestamp dans state.py
        return True

    except Exception as e:
        print(f"❌ Update error: {e}")
        # On ne propage pas l'erreur ici pour ne pas crasher le thread de polling
        # Mais le timestamp dans state.py ne sera pas mis à jour
        return False

def polling_loop():
    while True:
        print("🔄 Auto-refreshing Netatmo data...")
        if perform_update():
            print("✅ Auto-update complete")
        else:
            print("❌ Auto-update failed (Retrying in 5 min)")
        time.sleep(POLL_INTERVAL)

@app.route("/netatmo/state")
def netatmo_state():
    # C'EST ICI QUE TOUT SE JOUE 🧠
    # On vérifie si les données sont périmées (> 10 minutes)
    if is_data_stale(STALE_THRESHOLD):
        print("⚠️ Demande SmartThings : Données périmées -> Envoi erreur 502")
        # On renvoie 502 pour dire au Hub : "Je suis là, mais je n'arrive pas à joindre Netatmo"
        return jsonify({"error": "Data is stale (Netatmo unreachable)"}), 502
    
    return jsonify(get_state())

@app.route("/netatmo/refresh", methods=['POST', 'GET'])
def force_refresh():
    print("⚡ Manual Refresh requested by SmartThings...")
    if perform_update():
        print("✅ Manual update complete")
        return jsonify(get_state())
    else:
        # Si le refresh manuel échoue, on renvoie aussi une erreur 502
        return jsonify({"error": "Failed to refresh"}), 502

@app.route("/netatmo/set_temp", methods=['POST'])
def set_temp():
    try:
        content = request.json
        home_id = content.get('home_id')
        room_id = content.get('room_id')
        temp = content.get('temp')
        print(f"🎮 Set Temp: {temp}°C pour Room {room_id}")
        token = get_access_token()
        result = set_thermostat_temperature(token, home_id, room_id, temp)
        # On force une mise à jour immédiate du cache pour que l'appli voit le changement
        perform_update() 
        return jsonify({"status": "ok", "netatmo": result})
    except Exception as e:
        print(f"❌ Erreur Set Temp: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/netatmo/set_mode", methods=['POST'])
def set_mode():
    try:
        content = request.json
        home_id = content.get('home_id')
        mode = content.get('mode')
        print(f"🎮 Set Mode: {mode}")
        token = get_access_token()
        result = set_thermostat_mode(token, home_id, mode)
        perform_update()
        return jsonify({"status": "ok", "netatmo": result})
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
