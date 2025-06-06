# 🧠 OrganizrHSC – Intelligent Study Planner for Students

OrganizrHSC is a smart, Flask-based web application designed to help high school students efficiently plan their study schedules. With seamless integration of school assessment notifications, the app automatically extracts due dates from uploaded PDF documents and generates a personalized, balanced study timetable.

> Built as part of a Year 12 Software Engineering Major Work (HSC), this project blends modern frontend design with intelligent backend processing.

---

## 📌 Table of Contents

- [✨ Features](#-features)
- [📸 Screenshots](#-screenshots)
- [⚙️ Tech Stack](#️-tech-stack)
- [⚙️ Prerequisites](#️-prerequisites)



---

## ✨ Features

### 🔐 User Authentication
- Signup, login, and session management
- Frontend + backend form validation

### 📥 PDF Parsing
- Upload official school assessment notification PDFs
- Automatically extracts subjects, due dates, and task types using PDF parsing

### 📆 Study Schedule Generator
- Converts due dates into structured study plans
- Balances workload intelligently across available days
- Takes weekends and school hours into account

### 🎨 Modern UI
- Fully responsive design with Tailwind CSS
- Clean, accessible layout with polished modals, banners, and toasts
- Mobile-friendly experience

### 📊 Dashboard (WIP)
- Personalized view of your upcoming tasks
- Task completion tracking and subject breakdown

---

## 📸 Screenshots

> *(Screenshots coming soon)*

---

## ⚙️ Tech Stack

### 🧠 Backend
- **Flask** – Web framework
- **Werkzeug** – Secure password hashing
- **PyMuPDF (fitz)** – PDF parsing and text extraction
- **Jinja2** – Templating engine

### 🎨 Frontend
- **Tailwind CSS** – Utility-first CSS framework
- **Vanilla JavaScript** – Validation, dynamic UI, notifications

### 🗃️ Storage
- **SQLite** – Lightweight database for storing users and tasks

### 🔐 Security
- Password hashing
- Session control

---

### Prerequisites

Make sure you have the following installed:

- Python 3.9+
- `pip` package manager
- Git (optional, for cloning the repo)

