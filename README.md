# Noshiro DB Backend

This is the backend service for Noshiro's Database and Wiki, built with Django and Django REST Framework. It provides APIs and data management for the Noshiro platform.

## Features
- RESTful API for database and wiki operations
- User authentication and management
- Data synchronization with external sources (Bangumi, MyAnimeList, VNDB, etc.)
- Modular provider and service architecture
- PostgreSQL database support

## Requirements
- Python 3.10+
- PostgreSQL
- pip (Python package manager)

## Setup
1. Clone the repository:
	```bash
	git clone <repo-url>
	cd noshiro-db-backend
	```
2. Create and activate a virtual environment (recommended):
	```bash
	python -m venv venv
	source venv/bin/activate
	```
3. Install dependencies:
	```bash
	pip install -r requirements.txt
	```
4. Copy and configure your environment variables:
	```bash
	cp .env.example .env
	# Edit .env with your database and API keys
	```
5. Apply database migrations:
	```bash
	python manage.py migrate
	```
6. Run the development server:
	```bash
	python manage.py runserver
	```

## Project Structure
- `config/` — Django project settings and configuration
- `index/` — Core models and logic
- `sync/` — Data synchronization logic, providers, and services
- `users/` — User management and authentication
