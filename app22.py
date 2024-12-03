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
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    cursor.execute('SELECT board FROM games WHERE code=?', (game_code,))
    board = cursor.fetchone()
    conn.close()
    return list(board[0]) if board else None

def get_player_names(game_code):
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    cursor.execute('SELECT player1, player2 FROM games WHERE code=?', (game_code,))
    players = cursor.fetchone()
    conn.close()
    return {"player1": players[0], "player2": players[1]} if players else {}

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
    return list(board), game[4]  # Возвращаем также current_turn (игрок, чей ход)

def init_db():
    # Создание таблицы для пользователей
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

    # Создание таблицы для игр
    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()
    cursor.execute(''' 
        CREATE TABLE IF NOT EXISTS games (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            p1 TEXT,
            p2 TEXT,
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

@app.route('/game/<game_code>/move', methods=['POST'])
def make_move(game_code):
    data = request.get_json()
    cell_index = data.get('cell_index')
    player = data.get('player')

    if (player == "p1"):
        player = "player1"
    elif (player == "p2"):
        player = "player2"
    else:
        player = "no"

    print(f"Получен запрос: игрок {player} делает ход в клетку {cell_index} в игре {game_code}")

    conn = sqlite3.connect('games.db')
    cursor = conn.cursor()

    cursor.execute('SELECT board, current_turn FROM games WHERE code=?', (game_code,))
    game_data = cursor.fetchone()

    if not game_data:
        conn.close()
        print("Игра не найдена")
        return jsonify({'success': False, 'error': 'Игра не найдена'})

    board, current_turn = list(game_data[0]), game_data[1]
    print(f"Текущее состояние доски: {''.join(board)}, сейчас ход игрока {current_turn}")

    # Проверка, чей сейчас ход
    if current_turn != player:
        conn.close()
        print("Ошибка: сейчас не ваш ход")
        return jsonify({'success': False, 'error': 'Сейчас не ваш ход'})

    if board[int(cell_index)] != '-':
        conn.close()
        print("Ошибка: клетка уже занята")
        return jsonify({'success': False, 'error': 'Клетка уже занята'})

    # Обновление доски в зависимости от игрока
    if player == 'player1':
        board[int(cell_index)] = 'X'  # 'X' для player1
    elif player == 'player2':
        board[int(cell_index)] = 'O'  # 'O' для player2

    next_turn = 'player2' if current_turn == 'player1' else 'player1'

    # Обновляем состояние игры в базе данных
    cursor.execute('UPDATE games SET board=?, current_turn=? WHERE code=?',
                   (''.join(board), next_turn, game_code))
    conn.commit()
    conn.close()

    print(f"После хода, новое состояние доски: {''.join(board)}, следующий ход: {next_turn}")
    return jsonify({'success': True, 'board': ''.join(board), 'next_turn': next_turn})

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

    if (player == "p1"):
        playerss="player1"
    elif (player == "p2"):
        playerss="player2"
    else:
        playerss="no"

    current_player_name = player_names.get(playerss, playerss)

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

@app.route('/get_messages/<game_code>', methods=['GET'])
def get_messages_route(game_code):
    messages = get_messages(game_code)  # Функция должна возвращать список сообщений из базы данных
    return jsonify({'messages': messages})

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