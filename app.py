from flask import Flask, jsonify, request, render_template, Response
from flask_cors import CORS
import json, os, csv
from io import StringIO
from datetime import datetime
from threading import Lock

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)
DATA_FILE = "students.json"
LOCK = Lock()

# ---------- data helpers ----------
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # if broken JSON, back it up and return empty
        try:
            os.rename(DATA_FILE, DATA_FILE + ".bak")
        except:
            pass
        return []

def save_data(students):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(students, f, indent=2)

def get_next_id(students):
    if not students: return 1
    return max((s.get("id",0) for s in students), default=0) + 1

def find_by_roll(students, roll):
    if roll is None: return None
    r = str(roll).strip().lower()
    for s in students:
        if str(s.get("roll","")).strip().lower() == r:
            return s
    return None

# ---------- pages ----------
@app.route("/")
def index():
    return render_template("index.html")

# ---------- API ----------
@app.route("/api/students", methods=["GET"])
def api_list():
    with LOCK:
        students = load_data()
    return jsonify(students)

@app.route("/api/students", methods=["POST"])
def api_add():
    data = request.get_json() or {}
    roll = str(data.get("roll","")).strip()
    name = str(data.get("name","")).strip()
    if not roll or not name:
        return jsonify({"error":"roll and name required"}), 400
    with LOCK:
        students = load_data()
        if find_by_roll(students, roll):
            return jsonify({"error":"student exists"}), 409
        student = {
            "id": get_next_id(students),
            "roll": roll,
            "name": name,
            "email": str(data.get("email","")).strip(),
            "department": str(data.get("department","")).strip(),
            "year": int(data.get("year") or 1),
            "created_at": datetime.now().isoformat()
        }
        students.append(student)
        save_data(students)
    return jsonify(student), 201

@app.route("/api/students/<roll>", methods=["GET"])
def api_get(roll):
    with LOCK:
        s = find_by_roll(load_data(), roll)
    if not s:
        return jsonify({"error":"not found"}), 404
    return jsonify(s)

@app.route("/api/students/<roll>", methods=["PUT"])
def api_update(roll):
    data = request.get_json() or {}
    with LOCK:
        students = load_data()
        s = find_by_roll(students, roll)
        if not s: return jsonify({"error":"not found"}), 404
        # update fields
        if "name" in data and str(data["name"]).strip(): s["name"] = str(data["name"]).strip()
        if "email" in data: s["email"] = str(data["email"]).strip()
        if "department" in data: s["department"] = str(data["department"]).strip()
        if "year" in data:
            try: s["year"] = int(data["year"])
            except: pass
        save_data(students)
    return jsonify(s)

@app.route("/api/students/<roll>", methods=["DELETE"])
def api_delete(roll):
    with LOCK:
        students = load_data()
        s = find_by_roll(students, roll)
        if not s: return jsonify({"error":"not found"}), 404
        students = [x for x in students if str(x.get("roll","")).strip().lower() != str(roll).strip().lower()]
        save_data(students)
    return jsonify({"deleted": roll})

# ---------- CSV export endpoint (server-side) ----------
@app.route("/api/students/export", methods=["GET"])
def api_export_csv():
    students = load_data()
    si = StringIO()
    writer = csv.writer(si)
    header = ['id','roll','name','email','department','year','created_at']
    writer.writerow(header)
    for s in students:
        writer.writerow([s.get(h,'') for h in header])
    output = si.getvalue()
    si.close()
    return Response(output, mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=students.csv"})

# ---------- run ----------
if __name__ == "__main__":
    # debug True for development. Use python app.py to run.
    app.run(debug=True, port=5000)
