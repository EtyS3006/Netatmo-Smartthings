import time
from threading import Lock

_state = {}
_last_update_time = 0  # Timestamp de la dernière mise à jour réussie
_lock = Lock()

def update_state(data):
    global _last_update_time
    with _lock:
        _state.clear()
        _state.update(data)
        _last_update_time = time.time() # On note l'heure du succès

def get_state():
    with _lock:
        return _state.copy()

def is_data_stale(seconds_allowed):
    """Retourne Vrai si les données sont plus vieilles que la limite autorisée"""
    with _lock:
        if _last_update_time == 0:
            return True # Jamais mis à jour
        age = time.time() - _last_update_time
        return age > seconds_allowed
