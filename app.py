"""Samah Ayurveda – Flask application.

Routes
------
GET  /                  Single-page website
GET  /api/services      Service catalogue (JSON)
POST /api/appointments  Store an appointment request (MongoDB)
POST /api/contact       Store a contact message (MongoDB)

If MongoDB is unreachable the data is appended to data/<collection>.jsonl so
that no enquiry is lost during development. Check the logs when that happens.
"""
import json
import logging
import os
import re
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
log = logging.getLogger("samah")
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------- site config
SITE = {
    "name": "Samah Ayurveda",
    "tagline": "Ancient Wisdom for a Healthier, Happier You",
    "address_lines": ["Lalbagh, Mangalore", "Karnataka – 575003"],
    "phone_display": "+91 63636 25258",
    "phone_tel": "+916363625258",
    "whatsapp": "916363625258",
    # Instagram handles cannot contain "ḥ"; the poster uses plain "samah".
    "instagram_handle": "samah.ayurveda",
    "maps_query": "Samah Ayurveda, Lalbagh, Mangalore, Karnataka 575003",
}

# ------------------------------------------------------------------- services
SERVICES = [
    {
        "id": "postnatal-care",
        "name": "Postnatal Care",
        "summary": "Gentle recovery and nourishment for mother and baby.",
        "items": [
            "Mother & Baby Care",
            "Postpartum Recovery",
            "Nourishment & Rejuvenation",
            "Home Care Services Available",
        ],
    },
    {
        "id": "rejuvenation",
        "name": "Rejuvenation",
        "summary": "Restorative therapies for body, mind and vitality.",
        "items": [
            "Panchakarma & Detox",
            "Stress Relief & Relaxation",
            "Vitality & Wellness",
        ],
    },
    {
        "id": "cosmetology",
        "name": "Cosmetology",
        "summary": "Natural, Ayurveda-based skin and beauty care.",
        "items": [
            "Natural Skincare",
            "Facial & Skin Therapies",
            "Radiance & Skin Wellness",
        ],
    },
]
SERVICE_NAMES = {s["name"] for s in SERVICES} | {"General Consultation"}

# -------------------------------------------------------------------- storage
_client = None


def _collection(name):
    """Return a MongoDB collection, or None if the database is unreachable."""
    global _client
    try:
        if _client is None:
            _client = MongoClient(
                os.getenv("MONGO_URI", "mongodb://localhost:27017"),
                serverSelectionTimeoutMS=3000,
            )
        _client.admin.command("ping")
        return _client[os.getenv("MONGO_DB", "samah_ayurveda")][name]
    except PyMongoError as exc:
        log.warning("MongoDB unavailable (%s) – using file fallback", exc)
        _client = None
        return None


def save(collection_name, doc):
    """Persist a document. Returns True when stored in MongoDB."""
    doc["created_at"] = datetime.now(timezone.utc)
    coll = _collection(collection_name)
    if coll is not None:
        coll.insert_one(dict(doc))
        return True
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / f"{collection_name}.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, default=str, ensure_ascii=False) + "\n")
    return False


# ----------------------------------------------------------------- validation
PHONE_RE = re.compile(r"^(?:\+91|0)?[\s-]?[6-9]\d{4}[\s-]?\d{5}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TIME_SLOTS = {
    "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
    "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM",
}


def clean(value, limit=500):
    return str(value or "").strip()[:limit]


def validate_appointment(d):
    errors = {}
    if len(d["name"]) < 2:
        errors["name"] = "Please enter your full name."
    if not PHONE_RE.match(d["phone"]):
        errors["phone"] = "Enter a valid 10-digit Indian mobile number."
    if d["email"] and not EMAIL_RE.match(d["email"]):
        errors["email"] = "Enter a valid email address."
    if d["service"] not in SERVICE_NAMES:
        errors["service"] = "Please choose a service."
    try:
        if date.fromisoformat(d["date"]) < date.today():
            errors["date"] = "Choose today or a future date."
    except ValueError:
        errors["date"] = "Choose a preferred date."
    if d["time"] not in TIME_SLOTS:
        errors["time"] = "Choose a preferred time."
    return errors


# --------------------------------------------------------------------- routes
@app.get("/")
def index():
    return render_template(
        "index.html",
        site=SITE,
        maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        map_lat=os.getenv("MAP_LAT", "12.8830"),
        map_lng=os.getenv("MAP_LNG", "74.8430"),
    )


@app.get("/api/services")
def services():
    return jsonify({"services": SERVICES, "time_slots": sorted(TIME_SLOTS)})


@app.post("/api/appointments")
def appointments():
    payload = request.get_json(silent=True) or {}
    if payload.get("website"):  # honeypot – bots fill hidden fields
        return jsonify({"ok": True}), 201
    data = {
        "name": clean(payload.get("name"), 100),
        "phone": clean(payload.get("phone"), 20),
        "email": clean(payload.get("email"), 120),
        "service": clean(payload.get("service"), 60),
        "date": clean(payload.get("date"), 10),
        "time": clean(payload.get("time"), 10),
        "message": clean(payload.get("message"), 1000),
        "status": "new",
    }
    errors = validate_appointment(data)
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    try:
        save("appointments", data)
    except Exception:  # noqa: BLE001
        log.exception("Could not save appointment")
        return jsonify({"ok": False, "error": "Something went wrong. Please call us instead."}), 500
    return jsonify({"ok": True, "message": "Appointment request received."}), 201


@app.post("/api/contact")
def contact():
    payload = request.get_json(silent=True) or {}
    if payload.get("website"):
        return jsonify({"ok": True}), 201
    data = {
        "name": clean(payload.get("name"), 100),
        "email": clean(payload.get("email"), 120),
        "message": clean(payload.get("message"), 1500),
    }
    errors = {}
    if len(data["name"]) < 2:
        errors["name"] = "Please enter your name."
    if not EMAIL_RE.match(data["email"]):
        errors["email"] = "Enter a valid email address."
    if len(data["message"]) < 5:
        errors["message"] = "Please write a short message."
    if errors:
        return jsonify({"ok": False, "errors": errors}), 400
    try:
        save("contacts", data)
    except Exception:  # noqa: BLE001
        log.exception("Could not save contact message")
        return jsonify({"ok": False, "error": "Something went wrong. Please call us instead."}), 500
    return jsonify({"ok": True, "message": "Message received."}), 201


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", port=int(os.getenv("PORT", 5000)))
