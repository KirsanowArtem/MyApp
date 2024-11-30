from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
import os
from waitress import serve
from app22 import app

app = Flask(__name__)

# Встановлення секретного ключа через змінну середовища
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')

# Ініціалізація бази даних
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

# Виклик ініціалізації бази даних при запуску програми
init_db()

# Головна сторінка
@app.route('/')
def index():
    return render_template('index.html')

# Сторінка входу
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

# Сторінка реєстрації
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']

        # Перевірка на збіг паролів
        if password != confirm_password:
            flash('Паролі не збігаються.', 'error_confirm_password')
            return render_template('signup.html', error_confirm_password=True)

        # Спроба реєстрації
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

            # Вставка нового користувача
            cursor.execute('INSERT INTO users (username, password, email, last_login) VALUES (?, ?, ?, ?)',
                           (username, password, email, datetime.now()))
            conn.commit()

        flash('Реєстрація успішна. Будь ласка, увійдіть.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

# Сторінка привітання
@app.route('/welcome')
def welcome():
    if 'username' in session:
        username = session['username']
        if username == "Kirsanov Artem":
            return render_template('welcome.html', username=username, is_admin=True)
        return render_template('welcome.html', username=username)
    return redirect(url_for('index'))

# Сторінка адмін-панелі
@app.route('/admin')
def admin():
    if 'username' in session and session['username'] == "Kirsanov Artem" and request.args.get('password') == "12":
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        conn.close()
        return render_template('admin.html', users=users)
    return redirect(url_for('welcome'))

# Вихід
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# Запуск сервера
if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=10000)