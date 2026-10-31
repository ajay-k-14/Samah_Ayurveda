"""Samah Ayurveda – Flask application.

Routes
------
GET  /                  Website homepage
GET  /treatments/<id>   Treatment detail page
GET  /appointment       Appointment booking page
GET  /gallery           Filterable photo gallery
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
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, render_template, request
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
BOOKING_DB_PATH = Path(
    os.getenv("BOOKING_DB_PATH", str(DATA_DIR / "appointment_slots.sqlite3"))
).expanduser()

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
    "instagram_handle": "samahayurveda",
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
SERVICE_DETAILS = {
    "postnatal-care": {
        "description": "The weeks after birth are a time for rest, warmth and nourishment. Our postnatal programme draws on traditional Ayurvedic practice to help new mothers recover comfortably while their babies are cared for with equal tenderness. Every plan is shaped around the mother's health, delivery and daily needs.",
        "items": [
            "Traditional Ayurvedic postnatal therapies",
            "Mother & baby wellness",
            "Nourishing therapies",
            "Postpartum relaxation",
            "Recovery support",
            "Home care services",
        ],
        "image": "postnatal.jpg",
        "image_alt": "A new mother smiling with her baby",
        "heading": "Gentle Care for the Mother. Nurturing Care for the Baby.",
        "action": "Enquire About Postnatal Care",
    },
    "rejuvenation": {
        "description": "Ayurvedic rejuvenation works with the body's natural rhythms. Warm herbal oils, skilled hands and unhurried time help release tension and bring back energy, so you leave feeling lighter and more like yourself.",
        "items": [
            "Panchakarma",
            "Ayurvedic Massage",
            "Stress Relief",
            "Relaxation Therapies",
            "Detox Treatments",
            "Vitality & Wellness",
        ],
        "image": "rejuvenation.jpg",
        "image_alt": "Woman relaxing during an Ayurvedic herbal bolus massage",
        "heading": "Restore. Rejuvenate. Renew.",
        "action": "Book a Rejuvenation Session",
    },
    "cosmetology": {
        "description": "Healthy skin begins with balance. We use gentle, plant-based preparations and mindful techniques that care for your skin while supporting how you feel overall.",
        "items": [
            "Natural Skincare",
            "Ayurvedic Facials",
            "Skin Therapies",
            "Radiance Treatments",
            "Wellness-Based Beauty Care",
        ],
        "image": "cosmetology.jpg",
        "image_alt": "Ayurvedic facial with a natural herbal mask",
        "heading": "Natural Beauty, Rooted in Ayurveda",
        "action": "Discover Natural Beauty",
    },
}
PACKAGE_DETAILS = {
    "postnatal-care": {
        "title": "Postnatal Care Package",
        "summary": "A considered programme of care for a mother's recovery and the wellbeing of her baby.",
        "duration": "Choose 7, 14, 21 or 28 days; the schedule is shaped around individual needs and confirmed with the care team.",
        "therapies": [
            "Traditional Ayurvedic postnatal therapies",
            "Nourishing therapies and postpartum relaxation",
            "Mother and baby wellness support",
            "Home-care options, subject to availability",
        ],
        "benefits": [
            "Time and space to focus on rest and recovery",
            "A plan shaped around the mother's comfort and daily routine",
            "Support that considers both mother and baby",
        ],
        "includes": [
            "A conversation about care needs and preferences",
            "A recommended schedule for the agreed therapies",
            "Clear details on location, availability and fees before confirmation",
        ],
        "plans": [
            {"name": "7 days", "duration": "Schedule confirmed at consultation"},
            {"name": "14 days", "duration": "Schedule confirmed at consultation"},
            {"name": "21 days", "duration": "Schedule confirmed at consultation"},
            {"name": "28 days", "duration": "Schedule confirmed at consultation"},
        ],
    },
    "rejuvenation": {
        "title": "Rejuvenation Package",
        "summary": "A restorative course bringing together selected Ayurvedic therapies, unhurried care and time to reset.",
        "duration": "Choose 7, 14, 21 or 28 days; the schedule is finalized after consultation.",
        "therapies": [
            "Panchakarma and detox therapies, when suitable",
            "Ayurvedic massage and relaxation therapies",
            "Stress-relief and vitality-focused care",
            "A selection tailored with the practitioner",
        ],
        "benefits": [
            "A dedicated period for rest and relaxation",
            "Therapies selected to suit your goals and assessment",
            "A more structured approach to personal wellness",
        ],
        "includes": [
            "An initial consultation to discuss your needs",
            "A proposed therapy schedule for the selected duration",
            "Current pricing and confirmed inclusions before reservation",
        ],
        "plans": [
            {"name": "7 days", "duration": "Schedule confirmed at consultation"},
            {"name": "14 days", "duration": "Schedule confirmed at consultation"},
            {"name": "21 days", "duration": "Schedule confirmed at consultation"},
            {"name": "28 days", "duration": "Schedule confirmed at consultation"},
        ],
    },
    "cosmetology": {
        "title": "Ayurvedic Beauty Package",
        "summary": "A gentle, plant-led skin and beauty plan with treatments selected for your preferences and skin needs.",
        "duration": "Choose 7, 14, 21 or 28 days; the treatment schedule is discussed after a skin consultation.",
        "therapies": [
            "Natural skincare and Ayurvedic facials",
            "Skin therapies and radiance treatments",
            "Wellness-based beauty care",
            "Product and treatment choices discussed with the team",
        ],
        "benefits": [
            "A thoughtful routine built around your skin-care goals",
            "Gentle, plant-based preparations",
            "A chance to explore treatments at a comfortable pace",
        ],
        "includes": [
            "A discussion of skin-care preferences and sensitivities",
            "Recommended treatments and a suggested visit schedule",
            "Current pricing and confirmed inclusions before reservation",
        ],
        "plans": [
            {"name": "7 days", "duration": "Schedule confirmed at consultation"},
            {"name": "14 days", "duration": "Schedule confirmed at consultation"},
            {"name": "21 days", "duration": "Schedule confirmed at consultation"},
            {"name": "28 days", "duration": "Schedule confirmed at consultation"},
        ],
    },
}
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


def _booking_connection():
    BOOKING_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(BOOKING_DB_PATH, timeout=10)
    conn.execute("PRAGMA busy_timeout = 10000")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS appointment_slots (
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            appointment_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (appointment_date, appointment_time)
        )"""
    )
    if conn.execute("PRAGMA user_version").fetchone()[0] == 0:
        legacy_file = DATA_DIR / "appointments.jsonl"
        if legacy_file.exists():
            with legacy_file.open(encoding="utf-8") as stream:
                for line in stream:
                    try:
                        appointment = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    appointment_date = appointment.get("date", "")
                    appointment_time = appointment.get("time", "")
                    if appointment_date and appointment_time:
                        conn.execute(
                            """INSERT OR IGNORE INTO appointment_slots
                               (appointment_date, appointment_time, appointment_json, created_at)
                               VALUES (?, ?, ?, ?)""",
                            (appointment_date, appointment_time, line.strip(), appointment.get("created_at", "")),
                        )
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
    return conn


def booked_times(appointment_date):
    conn = _booking_connection()
    try:
        rows = conn.execute(
            "SELECT appointment_time FROM appointment_slots WHERE appointment_date = ?",
            (appointment_date,),
        )
        return {row[0] for row in rows}
    finally:
        conn.close()


def reserve_appointment(appointment):
    conn = _booking_connection()
    try:
        conn.execute(
            """INSERT INTO appointment_slots
               (appointment_date, appointment_time, appointment_json, created_at)
               VALUES (?, ?, ?, ?)""",
            (
                appointment["date"],
                appointment["time"],
                json.dumps(appointment, ensure_ascii=False),
                appointment["created_at"],
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()


# ----------------------------------------------------------------- validation
PHONE_RE = re.compile(r"^(?:\+91|0)?[\s-]?[6-9]\d{4}[\s-]?\d{5}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TIME_SLOTS = (
    "09:00 AM", "10:00 AM", "11:00 AM", "12:00 PM",
    "02:00 PM", "03:00 PM", "04:00 PM", "05:00 PM",
)


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
        services=SERVICES,
        maps_api_key=os.getenv("GOOGLE_MAPS_API_KEY", ""),
        map_lat=os.getenv("MAP_LAT", "12.8830"),
        map_lng=os.getenv("MAP_LNG", "74.8430"),
    )


@app.get("/treatments/<service_id>")
def service_detail(service_id):
    service = next((item for item in SERVICES if item["id"] == service_id), None)
    details = SERVICE_DETAILS.get(service_id)
    if service is None or details is None:
        abort(404)
    return render_template(
        "service.html",
        site=SITE,
        services=SERVICES,
        service={**service, **details},
    )


@app.get("/packages/<service_id>")
def package_detail(service_id):
    service = next((item for item in SERVICES if item["id"] == service_id), None)
    package = PACKAGE_DETAILS.get(service_id)
    if service is None or package is None:
        abort(404)
    return render_template(
        "package.html",
        site=SITE,
        services=SERVICES,
        service={**service, **SERVICE_DETAILS[service_id]},
        package=package,
    )


@app.get("/appointment")
def appointment():
    requested_service = request.args.get("service", "")
    if requested_service not in SERVICE_NAMES:
        requested_service = ""
    return render_template(
        "appointment.html",
        site=SITE,
        services=SERVICES,
        time_slots=TIME_SLOTS,
        selected_service=requested_service,
    )


@app.get("/gallery")
def gallery():
    return render_template("gallery.html", site=SITE, services=SERVICES)


@app.get("/api/services")
def services():
    return jsonify({"services": SERVICES, "time_slots": TIME_SLOTS})


@app.get("/api/availability")
def appointment_availability():
    requested_date = request.args.get("date", "")
    try:
        selected_date = date.fromisoformat(requested_date)
    except ValueError:
        return jsonify({"ok": False, "error": "Choose a valid date."}), 400
    if selected_date < date.today():
        return jsonify({"ok": False, "error": "Choose today or a future date."}), 400
    try:
        booked = booked_times(requested_date)
    except (sqlite3.Error, OSError):
        log.exception("Could not load appointment availability from %s", BOOKING_DB_PATH)
        return jsonify({"ok": False, "error": "Availability is temporarily unavailable."}), 503
    available = [slot for slot in TIME_SLOTS if slot not in booked]
    return jsonify({"ok": True, "date": requested_date, "available_slots": available})


@app.post("/api/appointments")
def appointments():
    payload = request.get_json(silent=True) or request.form.to_dict()
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
    data["created_at"] = datetime.now(timezone.utc).isoformat()
    try:
        if not reserve_appointment(data):
            return jsonify({"ok": False, "error": "That time has just been booked. Please choose another available time."}), 409
    except Exception:  # noqa: BLE001
        log.exception("Could not reserve appointment time in %s", BOOKING_DB_PATH)
        return jsonify({"ok": False, "error": "Availability is temporarily unavailable. Please call us instead."}), 503
    try:
        save("appointments", data)
    except Exception:  # noqa: BLE001
        log.exception("Appointment is reserved, but could not be copied to the enquiry store")
    return jsonify({"ok": True, "message": "Your request is received and this time is reserved. We will contact you to confirm."}), 201


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
