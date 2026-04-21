from flask import Flask, request, jsonify, render_template, redirect, session, send_file
from flask_cors import CORS
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json
import csv
import io
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
app.config['SESSION_PERMANENT'] = False
CORS(app, supports_credentials=True)

# ---------------- DATABASE CONFIGURATION ----------------
def get_db():
    """Get database connection - works with both SQLite (local) and PostgreSQL (Render)"""
    if 'DATABASE_URL' in os.environ:
        # Production: PostgreSQL on Render
        conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)
        return conn
    else:
        # Local development: SQLite
        conn = sqlite3.connect('task.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Initialize database tables"""
    conn = get_db()
    cursor = conn.cursor()
    
    if 'DATABASE_URL' in os.environ:
        # PostgreSQL syntax for Render
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                description TEXT,
                priority TEXT DEFAULT 'Medium',
                due_date DATE,
                category TEXT DEFAULT 'Personal',
                status TEXT DEFAULT 'To Do',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                action TEXT,
                task_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    else:
        # SQLite syntax for local development
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                description TEXT,
                priority TEXT DEFAULT 'Medium',
                due_date TEXT,
                category TEXT DEFAULT 'Personal',
                status TEXT DEFAULT 'To Do',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS activity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT,
                task_id INTEGER,
                details TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    conn.commit()
    conn.close()
    print("✓ Database initialized successfully")

# Initialize database
init_db()

# ---------------- HELPER FUNCTIONS ----------------
def log_activity(user_id, action, task_id=None, details=""):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO activity_log (user_id, action, task_id, details) VALUES (%s, %s, %s, %s)" 
            if 'DATABASE_URL' in os.environ else
            "INSERT INTO activity_log (user_id, action, task_id, details) VALUES (?, ?, ?, ?)",
            (user_id, action, task_id, details)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Activity log error: {e}")

# ---------------- AUTH ROUTES ----------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = request.form
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            if 'DATABASE_URL' in os.environ:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s)",
                    (data["username"], data["password"])
                )
            else:
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (data["username"], data["password"])
                )
            conn.commit()
            user_id = cursor.lastrowid if not 'DATABASE_URL' in os.environ else cursor.fetchone()['id'] if hasattr(cursor, 'fetchone') else None
            log_activity(user_id, "user_signup", details=f"User {data['username']} created account")
        except Exception as e:
            conn.close()
            return "User already exists"
        
        conn.close()
        return redirect("/login")
    
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.form
        conn = get_db()
        cursor = conn.cursor()
        
        if 'DATABASE_URL' in os.environ:
            cursor.execute(
                "SELECT * FROM users WHERE username=%s AND password=%s",
                (data["username"], data["password"])
            )
        else:
            cursor.execute(
                "SELECT * FROM users WHERE username=? AND password=?",
                (data["username"], data["password"])
            )
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session.permanent = False
            log_activity(user["id"], "user_login", details=f"User {user['username']} logged in")
            return redirect("/")
        else:
            return "Invalid credentials"
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    if "user_id" in session:
        log_activity(session["user_id"], "user_logout", details=f"User logged out")
    session.clear()
    return redirect("/login")

# ---------------- MAIN PAGE ----------------
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("index.html")

# ---------------- TASK ROUTES ----------------
@app.route("/get-tasks")
def get_tasks():
    if "user_id" not in session:
        return jsonify([])
    
    conn = get_db()
    cursor = conn.cursor()
    
    if 'DATABASE_URL' in os.environ:
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE user_id=%s 
            ORDER BY 
                CASE priority 
                    WHEN 'High' THEN 1 
                    WHEN 'Medium' THEN 2 
                    WHEN 'Low' THEN 3 
                END, 
                due_date ASC
        """, (session["user_id"],))
    else:
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE user_id=? 
            ORDER BY 
                CASE priority 
                    WHEN 'High' THEN 1 
                    WHEN 'Medium' THEN 2 
                    WHEN 'Low' THEN 3 
                END, 
                due_date ASC
        """, (session["user_id"],))
    
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/add-task", methods=["POST"])
def add_task():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    data = request.get_json()
    conn = get_db()
    cursor = conn.cursor()
    
    if 'DATABASE_URL' in os.environ:
        cursor.execute("""
            INSERT INTO tasks (user_id, title, description, priority, due_date, category, status) 
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            session["user_id"], 
            data.get("title", ""), 
            data.get("description", ""),
            data.get("priority", "Medium"),
            data.get("due_date", ""),
            data.get("category", "Personal"),
            "To Do"
        ))
    else:
        cursor.execute("""
            INSERT INTO tasks (user_id, title, description, priority, due_date, category, status) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"], 
            data.get("title", ""), 
            data.get("description", ""),
            data.get("priority", "Medium"),
            data.get("due_date", ""),
            data.get("category", "Personal"),
            "To Do"
        ))
    
    conn.commit()
    task_id = cursor.lastrowid if not 'DATABASE_URL' in os.environ else cursor.fetchone()['id'] if hasattr(cursor, 'fetchone') else None
    conn.close()
    
    log_activity(session["user_id"], "task_created", task_id, f"Task: {data.get('title')}")
    return {"message": "Task added", "id": task_id}

@app.route("/update-task/<int:id>", methods=["PUT"])
def update_task(id):
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    data = request.get_json()
    conn = get_db()
    cursor = conn.cursor()
    
    # Get old status for logging
    if 'DATABASE_URL' in os.environ:
        cursor.execute("SELECT title, status FROM tasks WHERE id=%s AND user_id=%s", (id, session["user_id"]))
    else:
        cursor.execute("SELECT title, status FROM tasks WHERE id=? AND user_id=?", (id, session["user_id"]))
    
    old_task = cursor.fetchone()
    
    if not old_task:
        conn.close()
        return {"error": "Task not found"}, 404
    
    new_status = data.get("status")
    completed_at = datetime.now().isoformat() if new_status == "Completed" else None
    
    if 'DATABASE_URL' in os.environ:
        cursor.execute(
            "UPDATE tasks SET status=%s, completed_at=%s WHERE id=%s AND user_id=%s",
            (new_status, completed_at, id, session["user_id"])
        )
    else:
        cursor.execute(
            "UPDATE tasks SET status=?, completed_at=? WHERE id=? AND user_id=?",
            (new_status, completed_at, id, session["user_id"])
        )
    
    conn.commit()
    conn.close()
    
    log_activity(session["user_id"], f"task_{new_status.lower()}", id, 
                f"Task: {old_task['title']} changed from {old_task['status']} to {new_status}")
    return {"message": "Task updated"}

@app.route("/edit-task/<int:id>", methods=["PUT"])
def edit_task(id):
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    data = request.get_json()
    conn = get_db()
    cursor = conn.cursor()
    
    if 'DATABASE_URL' in os.environ:
        cursor.execute("""
            UPDATE tasks 
            SET title=%s, description=%s, priority=%s, due_date=%s, category=%s 
            WHERE id=%s AND user_id=%s
        """, (data.get("title"), data.get("description"), data.get("priority"), 
              data.get("due_date"), data.get("category"), id, session["user_id"]))
    else:
        cursor.execute("""
            UPDATE tasks 
            SET title=?, description=?, priority=?, due_date=?, category=? 
            WHERE id=? AND user_id=?
        """, (data.get("title"), data.get("description"), data.get("priority"), 
              data.get("due_date"), data.get("category"), id, session["user_id"]))
    
    conn.commit()
    conn.close()
    
    log_activity(session["user_id"], "task_edited", id, f"Task edited: {data.get('title')}")
    return {"message": "Task updated"}

@app.route("/delete-task/<int:id>", methods=["DELETE"])
def delete_task(id):
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Get task title for logging
    if 'DATABASE_URL' in os.environ:
        cursor.execute("SELECT title FROM tasks WHERE id=%s AND user_id=%s", (id, session["user_id"]))
    else:
        cursor.execute("SELECT title FROM tasks WHERE id=? AND user_id=?", (id, session["user_id"]))
    
    task = cursor.fetchone()
    
    if task:
        if 'DATABASE_URL' in os.environ:
            cursor.execute("DELETE FROM tasks WHERE id=%s AND user_id=%s", (id, session["user_id"]))
        else:
            cursor.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (id, session["user_id"]))
        conn.commit()
        log_activity(session["user_id"], "task_deleted", id, f"Task deleted: {task['title']}")
    
    conn.close()
    return {"message": "Task deleted"}

# ---------------- EXPORT FEATURES ----------------
@app.route("/export-today-tasks")
def export_today_tasks():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    cursor = conn.cursor()
    
    if 'DATABASE_URL' in os.environ:
        cursor.execute("""
            SELECT title, description, priority, category, status, due_date 
            FROM tasks 
            WHERE user_id=%s AND due_date = %s
            ORDER BY priority
        """, (session["user_id"], today))
    else:
        cursor.execute("""
            SELECT title, description, priority, category, status, due_date 
            FROM tasks 
            WHERE user_id=? AND due_date = ?
            ORDER BY priority
        """, (session["user_id"], today))
    
    tasks = cursor.fetchall()
    conn.close()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Title', 'Description', 'Priority', 'Category', 'Status', 'Due Date'])
    
    for task in tasks:
        writer.writerow([task['title'], task['description'], task['priority'], 
                        task['category'], task['status'], task['due_date']])
    
    output.seek(0)
    
    log_activity(session["user_id"], "export_tasks", details=f"Exported {len(tasks)} tasks")
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'tasks_{today}.csv'
    )

@app.route("/export-all-tasks")
def export_all_tasks():
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    if 'DATABASE_URL' in os.environ:
        cursor.execute("""
            SELECT title, description, priority, category, status, due_date, created_at 
            FROM tasks 
            WHERE user_id=%s
            ORDER BY created_at DESC
        """, (session["user_id"],))
    else:
        cursor.execute("""
            SELECT title, description, priority, category, status, due_date, created_at 
            FROM tasks 
            WHERE user_id=?
            ORDER BY created_at DESC
        """, (session["user_id"],))
    
    tasks = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Title', 'Description', 'Priority', 'Category', 'Status', 'Due Date', 'Created At'])
    
    for task in tasks:
        writer.writerow([task['title'], task['description'], task['priority'], 
                        task['category'], task['status'], task['due_date'], task['created_at']])
    
    output.seek(0)
    
    log_activity(session["user_id"], "export_all_tasks", details=f"Exported {len(tasks)} tasks")
    
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'all_tasks_{datetime.now().strftime("%Y%m%d")}.csv'
    )

# ---------------- STATISTICS ----------------
@app.route("/get-stats")
def get_stats():
    if "user_id" not in session:
        return jsonify({}), 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Task statistics
    if 'DATABASE_URL' in os.environ:
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=%s", (session["user_id"],))
        total = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=%s AND status='Completed'", (session["user_id"],))
        completed = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=%s AND due_date=CURRENT_DATE", (session["user_id"],))
        due_today = cursor.fetchone()['count']
        
        # Priority breakdown
        cursor.execute("""
            SELECT priority, COUNT(*) FROM tasks 
            WHERE user_id=%s GROUP BY priority
        """, (session["user_id"],))
    else:
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=?", (session["user_id"],))
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND status='Completed'", (session["user_id"],))
        completed = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id=? AND due_date=date('now')", (session["user_id"],))
        due_today = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT priority, COUNT(*) FROM tasks 
            WHERE user_id=? GROUP BY priority
        """, (session["user_id"],))
    
    priority_stats = dict(cursor.fetchall())
    conn.close()
    
    return jsonify({
        'total': total,
        'completed': completed,
        'progress': total - completed,
        'due_today': due_today,
        'completion_rate': round((completed/total)*100, 1) if total > 0 else 0,
        'priority_stats': priority_stats
    })

# ---------------- ACTIVITY LOG ----------------
@app.route("/get-activity")
def get_activity():
    if "user_id" not in session:
        return jsonify([]), 401
    
    conn = get_db()
    cursor = conn.cursor()
    
    if 'DATABASE_URL' in os.environ:
        cursor.execute("""
            SELECT action, details, timestamp 
            FROM activity_log 
            WHERE user_id=%s 
            ORDER BY timestamp DESC 
            LIMIT 20
        """, (session["user_id"],))
    else:
        cursor.execute("""
            SELECT action, details, timestamp 
            FROM activity_log 
            WHERE user_id=? 
            ORDER BY timestamp DESC 
            LIMIT 20
        """, (session["user_id"],))
    
    logs = cursor.fetchall()
    conn.close()
    return jsonify([dict(log) for log in logs])

# ---------------- RUN ----------------
if __name__ == "__main__":
    print("✓ TaskFlow Pro Server Starting...")
    print(f"✓ Database: {'PostgreSQL (Production)' if 'DATABASE_URL' in os.environ else 'SQLite (Local)'}")
    print("✓ Server running at http://localhost:5000")
    app.run(debug=True)