# Backend API Contracts (Implementation Notes)

This file describes how APIs defined in the Wiki are implemented in the backend.

It is for backend developers only.

---

# Authentication

## /auth/login

- Validates email and password
- Uses bcrypt for password hashing
- Returns JWT token for authentication

---

## /auth/register

- Creates new user in database
- Checks if email already exists
- Hashes password before saving

---

# Workouts Module

- Located in: /modules/workouts
- Handles workout creation and retrieval
- Difficulty levels: beginner, intermediate, advanced

---

# Meals Module

- Located in: /modules/meals
- Stores nutritional data for meals
- Used for user diet tracking

---

# Database

- Stores users, workouts, meals
- Ensures relational consistency between user data and logs

---

# Notes

- This file must match Wiki API contracts
- Any backend change must be reflected in Wiki first
