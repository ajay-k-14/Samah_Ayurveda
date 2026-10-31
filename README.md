# Samah Ayurveda – clinic website

Flask + MongoDB backend with a vanilla HTML/CSS/JS front end, designed from the clinic's promotional poster.

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                   # edit values
python app.py                                          # http://127.0.0.1:5000
```
Appointment times are reserved atomically in `data/appointment_slots.sqlite3`, so only one booking can claim a date/time.
Appointment details are also stored in MongoDB (`MONGO_URI`); if MongoDB is unavailable, submissions are appended to
`data/*.jsonl` so nothing is lost while developing (a warning is logged).

## API
| Method | Path | Purpose |
|---|---|---|
| GET  | `/api/services` | Service catalogue + time slots |
| GET  | `/api/availability?date=YYYY-MM-DD` | Open appointment times for a date |
| POST | `/api/appointments` | name, phone, email?, service, date, time, message? |
| POST | `/api/contact` | name, email, message |

Appointment slots are unique by date and time. Appointment details are stored in the SQLite reservation database and
mirrored to MongoDB collections `appointments` and `contacts` (database `MONGO_DB`), or JSONL when MongoDB is unavailable.

## Treatment pages
The homepage links to the individual treatment pages at `/treatments/postnatal-care`,
`/treatments/rejuvenation`, and `/treatments/cosmetology`. These pages are also available
from the Treatments dropdown in the site navigation.
Appointment booking is available on its own page at `/appointment`.
The filterable photo gallery is available on its own page at `/gallery`.

## Google Maps
Set `GOOGLE_MAPS_API_KEY` in `.env` (never in source). The themed JavaScript map loads when a key is present;
otherwise a keyless embedded map is shown. Restrict the key by HTTP referrer in Google Cloud Console, and set
`MAP_LAT` / `MAP_LNG` to the clinic's exact pin (the defaults are approximate for Lalbagh).

## Things to replace before launch
- **Photos** in `static/images/` (hero, postnatal, rejuvenation, cosmetology, `gallery/`). They are currently cropped
  from the poster and are low resolution. Keep the same file names, ideally 1600px+ wide.
- **Logo** `static/images/logo.png` (cropped from the poster; a transparent PNG/SVG would be better).
- **Testimonials** in `templates/index.html` are samples – use real feedback with permission.
- Business details live in `SITE` at the top of `app.py`.

## Production
`gunicorn app:app` behind nginx, `FLASK_DEBUG=0`, and a MongoDB user with a password in `MONGO_URI`.
The host must run this Flask application and route `/api/*` requests to it; static-only hosting returns HTML pages instead of the JSON required for appointment availability and booking.

## Structure
```
app.py  requirements.txt  .env
templates/index.html  templates/service.html  templates/appointment.html  templates/gallery.html
templates/_site_header.html  templates/_site_footer.html
static/css/style.css  static/js/script.js  static/images/...
```
