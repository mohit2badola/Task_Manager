# 📋 TaskFlow Pro - Complete Project Synopsis

## Project Overview

TaskFlow Pro is a full-stack Task Management web application that allows users to create, manage, and track their tasks with features like priorities, categories, due dates, activity logging, and data export. The application follows a 3-tier architecture with Flask backend, SQLite database, and HTML/CSS/JavaScript frontend.

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | HTML5, CSS3, JavaScript | User interface and DOM manipulation |
| Backend | Flask (Python) | REST API, session management, business logic |
| Database | SQLite | Data persistence (tasks, users, activity logs) |
| Icons | Font Awesome 6 | Visual enhancements |
| Font | Google Fonts (Poppins) | Modern typography |
| Deployment | PythonAnywhere | Cloud hosting |

## System Architecture

┌─────────────────────────────────────────────────────────────┐
│                         USER BROWSER                        │
│                    (HTML/CSS/JavaScript)                    │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ Fetch API (JSON)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      FLASK BACKEND (app.py)                  │
│  Routes: /login, /signup, /get-tasks, /add-task,           │
│          /update-task, /delete-task, /edit-task,           │
│          /export-tasks, /get-stats, /get-activity          │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              │ SQLite3 Connection
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      SQLITE DATABASE                         │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │    users     │  │    tasks     │  │  activity_log   │   │
│  ├──────────────┤  ├──────────────┤  ├─────────────────┤   │
│  │ id (PK)      │  │ id (PK)      │  │ id (PK)         │   │
│  │ username     │  │ user_id (FK) │  │ user_id (FK)    │   │
│  │ password     │  │ title        │  │ action          │   │
│  │ created_at   │  │ description  │  │ details         │   │
│  └──────────────┘  │ priority     │  │ timestamp       │   │
│                    │ due_date     │  └─────────────────┘   │
│                    │ category     │                         │
│                    │ status       │                         │
│                    │ created_at   │                         │
│                    │ completed_at │                         │
│                    └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘

## Complete app.py Explained

### Section 1: Imports

```python
from flask import Flask, request, jsonify, render_template, redirect, session
from flask_cors import CORS
import sqlite3
from datetime import datetime
import csv
import io
import os
