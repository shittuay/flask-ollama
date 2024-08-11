from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import sqlite3
import os
import ollama as ol
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secret key for session management

# Initialize the SQLite database
DB_PATH = 'chat_history.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized with users and history tables.")

def insert_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    hashed_password = generate_password_hash(password)
    c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()
    conn.close()

def authenticate_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, password FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()
    if user and check_password_hash(user[1], password):
        return user[0]  # Return user ID if authenticated
    return None

def insert_message(user_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)', (user_id, role, content))
    conn.commit()
    conn.close()

def fetch_history(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT role, content FROM history WHERE user_id = ?', (user_id,))
    rows = c.fetchall()
    conn.close()
    return rows

def clear_history(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM history WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

# Initialize the database
if not os.path.exists(DB_PATH):
    init_db()

def question(user_id, query):
    insert_message(user_id, 'user', query)
    history = fetch_history(user_id)
    ans = ""
    data = ol.chat(
        model='llama3',
        messages=[{'role': role, 'content': content} for role, content in history],
        stream=True 
    )

    for d in data:
        ans += d['message']['content']
    
    insert_message(user_id, 'assistant', ans)
    return ans

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    history = fetch_history(user_id)
    return render_template('index.html', history=history)

@app.route('/ask', methods=['POST'])
def ask():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_input = request.form['query']
    response = question(session['user_id'], user_input)
    return redirect(url_for('index'))

@app.route('/clear', methods=['POST'])
def clear():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    clear_history(session['user_id'])
    return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_id = authenticate_user(username, password)
        if user_id:
            session['user_id'] = user_id
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            insert_user(username, password)
            flash('Registration successful, please log in.')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists')
    return render_template('register.html')

if __name__ == '__main__':
    app.run(debug=True)
