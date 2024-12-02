import string
import random
from flask import Flask, request, jsonify, render_template, request, redirect, url_for, flash, session
import sqlite3
from datetime import datetime
import os
from waitress import serve

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_secret_key')
player_names = {}
game_messages = {}

def add_message(game_code, message):
    if game_code not in game_messages:
        game_messages[game_code] = []
    game_messages[game_code].append(message)

def get_messages(game_code):
    return game_messages.get(game_code, [])

def get_game_board(game_code):
    return [' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ', ' ']

def get_player_names(game_code):
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()

    cursor.execute("SELECT player1, player2 FROM games WHERE code = ?", (game_code,))
    game_data = cursor.fetchone()
    conn.close()

    if game_data:
        return {
            'p1': game_data[0],
            'p2': game_data[1]
        }
    else:
        return {
            'p1': 'Игрок 1',
            'p2': 'Игрок 2'
        }


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

    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            player1 TEXT,
            player2 TEXT,
            board TEXT,
            current_turn TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.context_processor
def utility_functions():
    def generate_game_code():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return dict(generate_game_code=generate_game_code)

def get_game_data(game_code):
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games WHERE code=?', (game_code,))
    game = cursor.fetchone()
    conn.close()

    if game is None:
        return None

    board = game[3]
    if board is None:
        board = "---------"
    return list(board)

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
            flash('Неправильный пароль!', 'error')
            return render_template('main_admin_login.html')
    return render_template('main_admin_login.html')

@app.route('/new_tic_tac_toe')
def new_game():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('tic_tac_toe_new_game.html')

@app.route('/settings_tic_tac_toe/<game_code>')
def settings_tic_tac_toe(game_code):
    return render_template('tic_tac_toe_settings.html', game_code=game_code)

@app.route('/join_tic_tac_toe', methods=['GET', 'POST'])
def join_game():
    if request.method == 'POST':
        game_code = request.form.get('game_code')
        if game_code:
            return redirect(url_for('game_board', game_code=game_code, player='p2'))
        else:
            return "Код игры обязателен!", 400
    return render_template('tic_tac_toe_join_game.html')

@app.route('/tic_tac_toe/<game_code>/<player>', methods=['GET', 'POST'])
def tic_tac_toe_game(game_code, player):
    if request.method == 'POST':
        player2 = session['username']
        conn = sqlite3.connect('games.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET player2=? WHERE code=?', (player2, game_code))
        conn.commit()
        conn.close()
        return render_template('tic_tac_toe_board.html', game_code=game_code, player=player)
    game_data = get_game_data(game_code)
    return render_template('tic_tac_toe_board.html', game_data=game_data, game_code=game_code, player=player)

@app.route('/game_board/<game_code>/<player>/move/<int:cell_index>', methods=['POST'])
def make_move(game_code, player, cell_index):
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games WHERE code=?', (game_code,))
    game = cursor.fetchone()

    if game is None:
        return {'success': False, 'error': 'Игра не найдена'}, 404

    current_turn = game[4]  # player1 или player2
    board = list(game[3])  # Преобразуем строку в список

    # Проверяем, чей ход
    if (player == 'p1' and current_turn != 'player1') or (player == 'p2' and current_turn != 'player2'):
        return {'success': False, 'error': 'Не ваш ход'}, 400

    # Проверяем, что ячейка не занята
    if board[cell_index] != '-':
        return {'success': False, 'error': 'Эта ячейка уже занята'}, 400

    # Обновляем доску
    symbol = 'X' if player == 'p1' else 'O'
    board[cell_index] = symbol
    board_str = ''.join(board)

    # Обновляем доску в базе данных
    cursor.execute('UPDATE games SET board=?, current_turn=? WHERE code=?', (board_str, 'player2' if current_turn == 'player1' else 'player1', game_code))
    conn.commit()
    conn.close()

    return {'success': True, 'symbol': symbol}

@app.route('/game_board/<game_code>/<player>', methods=['GET', 'POST'])
def game_board(game_code, player):
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM games WHERE code=?', (game_code,))
    game = cursor.fetchone()
    conn.close()

    if game is None:
        if player == 'p1':
            player1_name = session['username']
            conn = sqlite3.connect('games.db')
            cursor = conn.cursor()
            cursor.execute('INSERT INTO games (code, player1, player2, board, current_turn) VALUES (?, ?, ?, ?, ?)',
                           (game_code, player1_name, None, "---------", "player1"))
            conn.commit()
            conn.close()
            return redirect(url_for('game_board', game_code=game_code, player='p1'))
        else:
            errors = f'<b><p style="font-size: 100px; color: red; ">Eror 404<br>Игра с таким кодом не найдена!</b>'
            return errors, 404

    if player == 'p2':
        player2_name = session['username']
        conn = sqlite3.connect('games.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET player2=? WHERE code=?', (player2_name, game_code))
        conn.commit()
        conn.close()

    player_names = get_player_names(game_code)
    current_player_name = player_names.get(player, player)

    if request.method == 'POST':
        message = request.form.get('message')
        if message:
            # Добавляем форматирование имени игрока и двоеточия
            formatted_message = f"<b>{current_player_name}:</b><br>  {message}"
            add_message(game_code, formatted_message)

    messages = get_messages(game_code)
    game_board = get_game_board(game_code)

    # Преобразуем символы новой строки на <br> для отображения
    messages = [message.replace('\n', '<br>') for message in messages]

    return render_template(
        'tic_tac_toe_board.html',
        game_code=game_code,
        player=player,
        messages=messages,
        game_board=game_board,
        player_name=current_player_name
    )

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=10000)
"""
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
"""