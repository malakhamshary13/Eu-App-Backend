# Eu-App-Backend
## Overview
This is the backend of the EU Health & Fitness application.  
It handles authentication, meal/workout management, and business logic.

---

## Tech Stack
- Python
- FastAPI (or your framework)
- Uvicorn
- SQLite / PostgreSQL

---

## Getting Started

### 1. Clone the repository

git clone https://github.com/malakhamshary13/Eu-App-Backend.git



---

### 2. Create virtual environment

python -m venv venv
source venv/bin/activate # Mac/Linux
venv\Scripts\activate # Windows


---

### 3. Install dependencies

pip install -r requirements.txt


---

### 4. Environment Variables

Create a `.env` file:


DATABASE_URL=sqlite:///./app.db
SECRET_KEY=your_secret_key



---

### 5. Run the server

uvicorn main:app --reload


Server will run at:

http://localhost:8000


---

## API Documentation
Once running, visit:

http://localhost:8000/docs


---

## Project Structure

////

---

## Branching Strategy
- `main` → stable
- `dev` → development
- `feature/*` → new features

Example:

feature/EU-17-meal-api


---

## Notes
- Ensure database is initialized before running
- Update `.env` for production configurations
