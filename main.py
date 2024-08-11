from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
import os
import ollama as ol

app = Flask(__name__)

# Initialize the SQLite database
DB_PATH = 'chat_history.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def insert_message(role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO history (role, content) VALUES (?, ?)', (role, content))
    conn.commit()
    conn.close()

def fetch_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT role, content FROM history')
    rows = c.fetchall()
    conn.close()
    return rows

def clear_history():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM history')
    conn.commit()
    conn.close()

# Initialize the database
if not os.path.exists(DB_PATH):
    init_db()

def question(query):
    insert_message('user', query)
    history = fetch_history()
    ans = ""
    data = ol.chat(
        model='llama3',
        messages=[{'role': role, 'content': content} for role, content in history],
        stream=True 
    )

    for d in data:
        ans += d['message']['content']
    
    insert_message('assistant', ans)
    return ans

@app.route('/')
def index():
    history = fetch_history()
    return render_template('index.html', history=history)

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.form['query']
    response = question(user_input)
    return redirect(url_for('index'))

@app.route('/clear', methods=['POST'])
def clear():
    clear_history()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
