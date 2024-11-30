from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import random
import string
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'


# Инициализация базы данных
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
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            player1 TEXT,
            player2 TEXT,
            board TEXT DEFAULT "---------",
            current_turn TEXT
        )
    ''')
    conn.commit()
    conn.close()


# Вызов инициализации базы данных при запуске приложения
init_db()


# Функция для генерации кода игры
def generate_game_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# Главная страница
@app.route('/')
def index():
    return render_template('main_index.html')

# Страница входа
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

    return render_template('main_login.html', error_username=error_username, error_password=error_password)

# Страница регистрации
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']

        # Проверка на совпадение паролей
        if password != confirm_password:
            flash('Пароли не совпадают.', 'error_confirm_password')
            return render_template('main_signup.html', error_confirm_password=True)

        # Попытка регистрации
        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                flash('Имя пользователя уже используется.', 'error_username')
                return render_template('main_signup.html', error_username=True)

            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('Эта почта уже зарегистрирована.', 'error_email')
                return render_template('main_signup.html', error_email=True)

            # Вставка нового пользователя
            cursor.execute('INSERT INTO users (username, password, email, last_login) VALUES (?, ?, ?, ?)',
                           (username, password, email, datetime.now()))
            conn.commit()

        flash('Регистрация успешна. Пожалуйста, авторизуйтесь.', 'success')
        return redirect(url_for('login'))
    return render_template('main_signup.html')

# Страница приветствия
@app.route('/welcome')
def welcome():
    if 'username' in session:
        username = session['username']
        if username == "Kirsanov Artem":
            return render_template('main_welcome.html', username=username, is_admin=True)
        return render_template('main_welcome.html', username=username)
    return redirect(url_for('index'))

# Страница админ-панели
@app.route('/admin')
def admin():
    if 'username' in session and session['username'] == "Kirsanov Artem" and request.args.get('password') == "12":
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        conn.close()
        return render_template('main_admin.html', users=users)
    return redirect(url_for('welcome'))

# Выход
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


# Создание новой игры
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
    return render_template('tic_tac_toe_created.html', game_code=game_code)


# Присоединение к существующей игре
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


# Страница игры
@app.route('/game/<game_code>')
def play_game(game_code):
    # Логика для отображения доски и контроля хода игры
    return render_template('tic_tac_toe.html', game_code=game_code)


if __name__ == '__main__':
    app.run(debug=True)
