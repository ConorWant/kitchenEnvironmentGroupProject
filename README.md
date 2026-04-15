## Kitchen Environment Django Dashboard

Modern Django website for fridge/freezer monitoring with:

- Login-required pages
- Dashboard cards for key metrics
- History table with server-side filters and sorting
- Fridge/freezer dropdown selector (including All Units)
- Database-first data loading with CSV fallback when DB is empty
- HTML/CSS-only frontend (no JavaScript or Tailwind)

## Project Structure

- `kitchen_site/`: Django project settings and root URLs
- `monitor/`: App with model, views, routes, and data service
- `templates/`: Global and app templates
- `static/css/site.css`: Styling
- `sensor_logger/`: CSV backup files

## Data Model

`SensorReading` fields:

- `timestamp`
- `temperature_c`
- `humidity_pct`
- `pressure_hpa`
- `door_status`
- `light_lux`
- `fridge_type`
- `fridge_number`

## Setup

1. Activate virtual environment:

```bash
source .venv/bin/activate
```

2. Install dependencies (if needed):

```bash
python -m pip install -r requirements.txt
```

3. Copy environment file:

```bash
cp .env.example .env
```

4. Run migrations:

```bash
python manage.py migrate
```

5. Create admin user:

```bash

```python manage.py createsuperuser

6. Start development server:

```bash
python manage.py runserver
```

7. Sign in at:

- `http://127.0.0.1:8000/accounts/login/`

8. Register a new user at :

- 'http://127.0.0.1:8000/register/'

# Possible "to-do":
# - Instructions for accessing your Django server from another device!

## Data Behavior

- If DB has records, all pages read from DB.
- If DB is empty, pages automatically read both CSV files in `sensor_logger/`.
- Dropdown filter allows selecting `All Units`, a specific fridge, or a specific freezer.

## Pages

- `/` Dashboard (latest cards + recent readings)
- `/history/` Full history with filter/sort/pagination
- `/management/` Admin-only management summary page
- `/admin/` Django admin for record management

## Future Expansion

The data service is structured so auto-sync from DB updates can be added later without changing templates.

# Setup Instructions

To install the required dependencies, use the following command:

```bash
python -m pip install -r requirements.txt
```

Please note that the sensor_logger dependencies are Raspberry Pi specific.