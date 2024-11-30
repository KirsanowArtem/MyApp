import string
import random
from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
import os
from waitress import serve

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')

# Функция для генерации кода игры
def generate_game_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

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

def create_games_table():
    conn = sqlite3.connect('games.db')  # Это вторая база данных
    cursor = conn.cursor()

    cursor.execute(''' 
    CREATE TABLE IF NOT EXISTS games (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT NOT NULL,
        player1 TEXT NOT NULL,
        player2 TEXT,
        current_turn TEXT NOT NULL
    )
    ''')

    conn.commit()
    conn.close()

# Функция для создания игры
def create_game():
    create_games_table()  # Создаем таблицу, если она не существует

    game_code = generate_game_code()  # Генерируем код игры

    # Подключаемся к базе данных и вставляем данные о новой игре
    conn = sqlite3.connect('games.db')  # Путь ко второй базе данных
    cursor = conn.cursor()

    cursor.execute('INSERT INTO games (code, player1, current_turn) VALUES (?, ?, ?)',
                   (game_code, 'Player1', '⭕️'))
    conn.commit()
    conn.close()

# Вызовите функцию создания игры
create_game()

init_db()

def generate_game_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@app.route('/')
def index():
    return render_template('main_index.html')

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

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        email = request.form['email']

        if password != confirm_password:
            flash('Паролі не збігаються.', 'error_confirm_password')
            return render_template('main_signup.html', error_confirm_password=True)

        with sqlite3.connect('users.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                flash('Це ім’я вже використовується.', 'error_username')
                return render_template('main_signup.html', error_username=True)

            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            if cursor.fetchone():
                flash('Ця пошта вже зареєстрована.', 'error_email')
                return render_template('main_signup.html', error_email=True)

            cursor.execute('INSERT INTO users (username, password, email, last_login) VALUES (?, ?, ?, ?)',
                           (username, password, email, datetime.now()))
            conn.commit()

        flash('Реєстрація успішна. Будь ласка, увійдіть.', 'success')
        return redirect(url_for('login'))
    return render_template('main_signup.html')

@app.route('/welcome')
def welcome():
    if 'username' in session:
        username = session['username']
        if username == "Kirsanov Artem":
            return render_template('main_welcome.html', username=username, is_admin=True)
        return render_template('main_welcome.html', username=username)
    return redirect(url_for('index'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form['password']
        if password == "12":
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users')
            users = cursor.fetchall()
            conn.close()
            return render_template('main_admin.html', users=users)
        else:
            flash('Неправильный пароль!', 'error')  # Сообщение об ошибке
            return render_template('main_admin_login.html')  # Перенаправляем обратно на страницу с формой ввода пароля
    return render_template('main_admin_login.html')  # Если метод GET, показываем форму для ввода пароля

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/new_game')
def new_game():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('tic_tac_toe_new_game.html')  # Эта страница с двумя кнопками


@app.route('/join_tic_tac_toe', methods=['GET', 'POST'])
def join_tic_tac_toe():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        game_code = request.form['game_code']
        username = session['username']
        conn = sqlite3.connect('games.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM games WHERE code=?', (game_code,))
        game = cursor.fetchone()

        if game:
            cursor.execute('UPDATE games SET player2=? WHERE code=?', (username, game_code))
            conn.commit()
            conn.close()
            return redirect(url_for('game_board', game_code=game_code, player='p2'))
        else:
            flash('Неверный код игры.')
            conn.close()
            return redirect(url_for('join_tic_tac_toe'))

    return render_template('tic_tac_toe_join.html')  # Эта страница с полем для ввода кода игры


@app.route('/create_game', methods=['POST'])
def create_game():
    if 'username' not in session:
        return redirect(url_for('login'))

    game_code = generate_game_code()
    username = session['username']
    conn = sqlite3.connect('games.db')  # Предполагаем, что игры хранятся в другой базе данных
    cursor = conn.cursor()
    cursor.execute('INSERT INTO games (code, player1, current_turn) VALUES (?, ?, ?)',
                   (game_code, username, username))
    conn.commit()
    conn.close()

    return redirect(url_for('settings_tic_tac_toe', game_code=game_code))

@app.route('/join_game', methods=['POST'])
def join_game():
    if 'username' not in session:
        return redirect(url_for('login'))

    game_code = request.form['game_code']
    username = session['username']
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games WHERE code=?', (game_code,))
    game = cursor.fetchone()

    if game:
        cursor.execute('UPDATE games SET player2=? WHERE code=?', (username, game_code))
        conn.commit()
        conn.close()
        return redirect(url_for('game_board', game_code=game_code, player='p2'))
    else:
        flash('Неверный код игры.')
        conn.close()
        return redirect(url_for('new_game'))

@app.route('/settings_tic_tac_toe/<game_code>')
def settings_tic_tac_toe(game_code):
    # Здесь проверим, кто является игроком 1, если это первый игрок, он видит кнопку "Начать"
    return render_template('tic_tac_toe_settings.html', game_code=game_code)

@app.route('/games/<game_code>/<player>')
def game_board(game_code, player):
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games WHERE code=?', (game_code,))
    game = cursor.fetchone()

    if game:
        return render_template('tic_tac_toe_board.html', game_code=game_code, player=player, game=game)
    else:
        flash('Игра не найдена.')
        conn.close()
        return redirect(url_for('new_game'))


if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=10000)
"""
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
"""