import string
from random import random

from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
import os
from waitress import serve

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')

def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            email TEXT UNIQUE,
            last_login TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def generate_game_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_username = error_password = False
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username=?', (username,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            error_username = True
        elif user[2] != password:
            error_password = True
        else:
            session['username'] = username
            return redirect(url_for('welcome'))

    return render_template('login.html', error_username=error_username, error_password=error_password)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']

        if password != confirm_password:
            flash('Паролі не збігаються.', 'error_confirm_password')
            return render_template('signup.html', error_confirm_password=True)

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                flash('Це ім’я вже використовується.', 'error_username')
                return render_template('signup.html', error_username=True)

            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('Ця пошта вже зареєстрована.', 'error_email')
                return render_template('signup.html', error_email=True)

            cursor.execute('INSERT INTO users (username, password, email, last_login) VALUES (?, ?, ?, ?)',
                           (username, password, email, datetime.now()))
            conn.commit()

        flash('Реєстрація успішна. Будь ласка, увійдіть.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/welcome')
def welcome():
    if 'username' in session:
        username = session['username']
        if username == "Kirsanov Artem":
            return render_template('welcome.html', username=username, is_admin=True)
        return render_template('welcome.html', username=username)
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', users=users)


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/new_game')
def new_game():
    if 'username' not in session:
        return redirect(url_for('login'))

    game_code = generate_game_code()
    username = session['username']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO games (code, player1, current_turn) VALUES (?, ?, ?)',
                   (game_code, username, username))
    conn.commit()
    conn.close()
    return render_template('game_created.html', game_code=game_code)

@app.route('/join_game', methods=['POST'])
def join_game():
    if 'username' not in session:
        return redirect(url_for('login'))

    game_code = request.form.get('game_code')
    username = session['username']

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games WHERE code=? AND player2 IS NULL', (game_code,))
    game = cursor.fetchone()

    if game:
        cursor.execute('UPDATE games SET player2 = ? WHERE code = ?', (username, game_code))
        conn.commit()
        conn.close()
        return redirect(url_for('play_game', game_code=game_code))
    else:
        conn.close()
        flash('Игра не найдена или уже началась.', 'error')
        return redirect(url_for('welcome'))

@app.route('/game/<game_code>')
def play_game(game_code):
    return render_template('tic_tac_toe.html', game_code=game_code)
"""
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=10000)
"""
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
