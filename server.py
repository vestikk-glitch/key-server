from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json
import random
import string
import os

app = Flask(__name__)
KEYS_FILE = "keys.json"

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
    
@app.route('/generate', methods=['GET'])
def generate():
    days = int(request.args.get('days', 30))
    key = generate_key()
    expiry = (datetime.now() + timedelta(days=days)).isoformat()
    keys = load_keys()
    keys[key] = {"expiry": expiry, "active": True}
    save_keys(keys)
    return jsonify({"key": key, "expiry": expiry, "message": f"Key valid for {days} days"})

@app.route('/check', methods=['GET'])
def check():
    key = request.args.get('key')
    keys = load_keys()
    if key not in keys:
        return jsonify({"valid": False, "reason": "Key not found"})
    key_data = keys[key]
    expiry_date = datetime.fromisoformat(key_data["expiry"])
    if datetime.now() > expiry_date:
        return jsonify({"valid": False, "reason": "Key expired"})
    if not key_data["active"]:
        return jsonify({"valid": False, "reason": "Key deactivated"})
    return jsonify({"valid": True, "expiry": key_data["expiry"], "message": "Access granted"})

@app.route('/list', methods=['GET'])
def list_keys():
    keys = load_keys()
    result = []
    for k, v in keys.items():
        result.append({"key": k, "expiry": v["expiry"], "active": v["active"]})
    return jsonify(result)

@app.route('/revoke', methods=['GET'])
def revoke():
    key = request.args.get('key')
    keys = load_keys()
    if key in keys:
        keys[key]["active"] = False
        save_keys(keys)
        return jsonify({"success": True, "message": "Key revoked"})
    return jsonify({"success": False, "message": "Key not found"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
