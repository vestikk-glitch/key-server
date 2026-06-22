from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json
import random
import string
import os

app = Flask(__name__)
KEYS_FILE = "keys.json"

# Твой секретный пароль (замени на свой)
SECRET_PASSWORD = "1337"

def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=4)

def generate_key():
    return 'TOOL-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))

# ═══════════════════════════════════════
#  ПИНГ (ЧТОБЫ СЕРВЕР НЕ ЗАСЫПАЛ)
# ═══════════════════════════════════════
@app.route('/ping', methods=['GET'])
def ping():
    return jsonify({"status": "alive", "time": datetime.now().isoformat()})

# ═══════════════════════════════════════
#  ГЕНЕРАЦИЯ КЛЮЧА
# ═══════════════════════════════════════
@app.route('/generate', methods=['GET'])
def generate():
    password = request.args.get('password', '')
    if password != SECRET_PASSWORD:
        return jsonify({"error": "Invalid password"}), 403
    
    days = int(request.args.get('days', 30))
    key = generate_key()
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    keys = load_keys()
    keys[key] = {"expiry": expiry, "active": True, "hwid": None}
    save_keys(keys)
    return jsonify({"key": key, "expiry": expiry, "message": f"Key valid for {days} days"})

# ═══════════════════════════════════════
#  ДОБАВЛЕНИЕ КЛЮЧА ВРУЧНУЮ
# ═══════════════════════════════════════
@app.route('/addkey', methods=['GET'])
def addkey():
    password = request.args.get('password', '')
    if password != SECRET_PASSWORD:
        return jsonify({"error": "Invalid password"}), 403
    
    key = request.args.get('key', '')
    days = int(request.args.get('days', 30))
    
    if not key:
        return jsonify({"error": "Key parameter required"}), 400
    
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    keys = load_keys()
    
    if key in keys:
        return jsonify({"error": "Key already exists"}), 400
    
    keys[key] = {"expiry": expiry, "active": True, "hwid": None}
    save_keys(keys)
    return jsonify({"message": "Key added", "key": key, "expiry": expiry})

# ═══════════════════════════════════════
#  АКТИВАЦИЯ КЛЮЧА (HWID)
# ═══════════════════════════════════════
@app.route('/check', methods=['GET'])
def check():
    key = request.args.get('key')
    hwid = request.args.get('hwid', '')
    keys = load_keys()
    
    if key not in keys:
        return jsonify({"valid": False, "reason": "Key not found"})
    
    key_data = keys[key]
    expiry_date = datetime.fromisoformat(key_data["expiry"])
    
    if datetime.now() > expiry_date:
        return jsonify({"valid": False, "reason": "Key expired"})
    
    if not key_data["active"]:
        return jsonify({"valid": False, "reason": "Key deactivated"})
    
    # Проверка HWID
    if key_data["hwid"] is None:
        key_data["hwid"] = hwid
        keys[key] = key_data
        save_keys(keys)
        return jsonify({"valid": True, "expiry": key_data["expiry"], "message": "Key activated and bound to device"})
    
    if key_data["hwid"] != hwid:
        return jsonify({"valid": False, "reason": "Key is bound to another device"})
    
    return jsonify({"valid": True, "expiry": key_data["expiry"], "message": "Access granted"})

# ═══════════════════════════════════════
#  АКТИВИРОВАТЬ ОТКЛЮЧЁННЫЙ КЛЮЧ
# ═══════════════════════════════════════
@app.route('/activate', methods=['GET'])
def activate():
    password = request.args.get('password', '')
    if password != SECRET_PASSWORD:
        return jsonify({"error": "Invalid password"}), 403
    
    key = request.args.get('key', '')
    keys = load_keys()
    if key not in keys:
        return jsonify({"error": "Key not found"}), 404
    
    keys[key]["active"] = True
    save_keys(keys)
    return jsonify({"message": f"Key {key} activated", "key": key})

# ═══════════════════════════════════════
#  ПРОДЛИТЬ КЛЮЧ
# ═══════════════════════════════════════
@app.route('/extend', methods=['GET'])
def extend():
    password = request.args.get('password', '')
    if password != SECRET_PASSWORD:
        return jsonify({"error": "Invalid password"}), 403
    
    key = request.args.get('key', '')
    days = int(request.args.get('days', 3))
    
    keys = load_keys()
    if key not in keys:
        return jsonify({"error": "Key not found"}), 404
    
    new_expiry = (datetime.now() + timedelta(days=days)).isoformat()
    keys[key]["expiry"] = new_expiry
    keys[key]["active"] = True
    save_keys(keys)
    
    return jsonify({
        "message": f"Key extended by {days} days",
        "key": key,
        "new_expiry": new_expiry
    })

# ═══════════════════════════════════════
#  ОТОЗВАТЬ КЛЮЧ (ОТКЛЮЧИТЬ)
# ═══════════════════════════════════════
@app.route('/revoke', methods=['GET'])
def revoke():
    key = request.args.get('key')
    keys = load_keys()
    if key in keys:
        keys[key]["active"] = False
        save_keys(keys)
        return jsonify({"success": True, "message": "Key revoked"})
    return jsonify({"success": False, "message": "Key not found"})

# ═══════════════════════════════════════
#  УДАЛИТЬ КЛЮЧ ПОЛНОСТЬЮ
# ═══════════════════════════════════════
@app.route('/deletekey', methods=['GET'])
def deletekey():
    password = request.args.get('password', '')
    if password != SECRET_PASSWORD:
        return jsonify({"error": "Invalid password"}), 403
    
    key = request.args.get('key', '')
    keys = load_keys()
    if key not in keys:
        return jsonify({"error": "Key not found"}), 404
    
    del keys[key]
    save_keys(keys)
    return jsonify({"message": f"Key {key} deleted"})

# ═══════════════════════════════════════
#  СБРОСИТЬ HWID (ОТВЯЗАТЬ ОТ УСТРОЙСТВА)
# ═══════════════════════════════════════
@app.route('/resethwid', methods=['GET'])
def resethwid():
    password = request.args.get('password', '')
    if password != SECRET_PASSWORD:
        return jsonify({"error": "Invalid password"}), 403
    
    key = request.args.get('key', '')
    keys = load_keys()
    if key not in keys:
        return jsonify({"error": "Key not found"}), 404
    
    keys[key]["hwid"] = None
    save_keys(keys)
    return jsonify({"message": f"HWID reset for key {key}", "key": key})

# ═══════════════════════════════════════
#  СПИСОК ВСЕХ КЛЮЧЕЙ
# ═══════════════════════════════════════
@app.route('/list', methods=['GET'])
def list_keys():
    keys = load_keys()
    result = []
    for k, v in keys.items():
        result.append({
            "key": k,
            "expiry": v["expiry"],
            "active": v["active"],
            "hwid": v.get("hwid", "Not bound")
        })
    return jsonify(result)

# ═══════════════════════════════════════
#  ИНФОРМАЦИЯ О КОНКРЕТНОМ КЛЮЧЕ
# ═══════════════════════════════════════
@app.route('/info', methods=['GET'])
def info():
    password = request.args.get('password', '')
    if password != SECRET_PASSWORD:
        return jsonify({"error": "Invalid password"}), 403
    
    key = request.args.get('key', '')
    keys = load_keys()
    if key not in keys:
        return jsonify({"error": "Key not found"}), 404
    
    key_data = keys[key]
    return jsonify({
        "key": key,
        "expiry": key_data["expiry"],
        "active": key_data["active"],
        "hwid": key_data.get("hwid", "Not bound")
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
