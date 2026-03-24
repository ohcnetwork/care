# Running CARE in GitHub Codespaces (Manual Setup)

CARE officially requires Python 3.13 and Docker, but GitHub Codespaces default environment uses Python 3.12 and may not have Docker available.

This guide helps contributors explore CARE **without Docker**, using SQLite as a temporary database.

## Step 1 - Create a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```
## Step 2 - Upgrade pip
```bash
pip install --upgrade pip
```
## Step 3 - Install core dependencies
```bash
pip install django python-dotenv requests
```
> ⚠️ Note: Some features may not work because project offically requires Python 3.13

## Step 4 - Configure .env for SQLite
```bash
cp .env.example .env
export DJANGO_READ_DOT_ENV_FILE=True
```
Edit .env and set the database URL:
```env
DATABASE_URL=sqlite:///db.sqlite3
```

## Step 5 - Run migrations
```bash
python manage.py migrate
```
## Step 6 - Start development server
```bash
python manage.py runserver 0.0.0.0:8000
```
Open port 8000 in Codespaces you should see the app running (note some features may not work without Docker).

## Note for Contributors

> ⚠️ Note: The manual Codespaces setup may not run the full application.
> Some features require Python 3.13 and Docker. This setup is intended.
> for exploring the code and experimenting with non-critical parts of CARE.
