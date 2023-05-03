from flask import Flask, render_template, request, redirect, url_for, g
import os
import sqlite3
import random
from apscheduler.schedulers.background import BackgroundScheduler


app_info = {
    'db_file' : 'C:/Users/Kinga/PycharmProjects/Zadanie_Programistyczne/database.db'
}

app = Flask(__name__)

app.config['SECRET_KEY'] = 'QWEASD123'
# ustawienie scieżki do bazy danych SQLite3
db_path = os.path.join(os.path.dirname(__file__), 'database.db')

def get_db():
    if not hasattr(g, 'sqlite_db'):
        conn = sqlite3.connect(app_info['db_file'])
        conn.row_factory = sqlite3.Row
        g.sqlite_db = conn
    return g.sqlite_db

@app.teardown_appcontext
def close_db(error):

    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


def usun_rekordy_z_tabeli():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("DELETE FROM zwyciezcy")
    conn.commit()
    conn.close()

# inicjalizacja schedulera
scheduler = BackgroundScheduler()
scheduler.add_job(func=usun_rekordy_z_tabeli, trigger='cron', hour=23, minute=59)

# uruchomienie schedulera
scheduler.start()

@app.before_first_request
def create_tables():
    # utworzenie tabeli photos w bazie danych, jeśli nie istnieje
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS photos (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    conn.commit()
    conn.close()


@app.route('/')
def index():
    # pobierz z bazy danych informacje o dodanych zdjeciach
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT name FROM photos')
    photo_names = c.fetchall()
    photos = []
    for name in photo_names:
        c.execute(f'SELECT * FROM {name[0]}')
        photos += c.fetchall()
    conn.close()

    # wyswietl szablon strony index.html
    return render_template('index.html')


@app.route('/add_photo', methods=['GET', 'POST'])
def add_photo():
    if request.method == 'POST':
        # pobierz przesłane zdjecie i nazwe
        photo = request.files['photo']
        name = request.form['name']

        # zapisz przeslane zdjecie pod nowa nazwa w folderze static
        photo.save(os.path.join('static', name + '.jpg'))

        # dodaj informacje o zdjeciu do bazy danych
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(f'CREATE TABLE IF NOT EXISTS {name} (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT, losy TEXT)')
        c.execute(f'INSERT INTO photos (name) VALUES (?)', (name,))
        c.execute(f'INSERT INTO {name} (path) VALUES (?)', (os.path.join('static', name + '.jpg'),))
        conn.commit()
        conn.close()

        # przekieruj uzytkownika na strone glowna
        return redirect(url_for('add_photo'))

    # wyswietl szablon strony add_photo.html z formularzem do dodawania zdjec
    return render_template('add_photo.html')


@app.route('/wybierz', methods=['GET', 'POST'])
def wybierz():
    if request.method == 'POST':
        # pobierz nazwę zdjęcia i wartość losu
        name = request.form['name']
        los = request.form['los']

        # dodaj wartość losu jako nowy rekord do tabeli o nazwie zdjęcia
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute(f'INSERT INTO {name} (path, losy) VALUES (?, ?)', (os.path.join('static', name + '.jpg'), request.form['los']))
        conn.commit()
        conn.close()

        # przekieruj użytkownika na stronę główną
        return redirect(url_for('wybierz'))

    # pobierz informacje o zdjeciach z bazy danych
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT name FROM photos')
    photo_names = c.fetchall()
    photos = []
    for name in photo_names:
        c.execute(f'SELECT path FROM {name[0]}')
        path = c.fetchone()
        if path is not None:
            photos.append({'name': name[0], 'path': path[0]})
    conn.close()

    # wyswietl szablon strony wybierz.html z lista zdjec
    return render_template('wybierz.html', photos=photos)

@app.route('/take_part/<name>', methods=['POST'])
def take_part(name):
    # pobierz dane z pola tekstowego
    los = request.form['los']

    # dodaj dane do kolumny "los" w tabeli o nazwie zdjęcia
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(f'UPDATE {name} SET losy = ? WHERE id = (SELECT MAX(id) FROM {name})', (los,))
    conn.commit()
    conn.close()

    # przekieruj użytkownika na stronę główną
    return redirect(url_for('wybierz'))

@app.route('/history', methods=['GET', 'POST'])
def history():
    # pobierz informacje o zdjęciach z bazy danych
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('SELECT name FROM photos')
    photo_names = c.fetchall()
    photos = []
    for name in photo_names:
        c.execute(f'SELECT path FROM {name[0]}')
        path = c.fetchone()
        if path is not None:
            photos.append({'name': name[0], 'path': path[0]})
    conn.close()

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM zwyciezcy")
    zwyciezcy = c.fetchall()
    conn.close()

    # wyświetl szablon strony history.html bez listy zwycięzców
    return render_template('history.html', photos=photos, zwyciezcy=zwyciezcy)


@app.route('/delete_photo/<name>', methods=['POST'])
def delete_photo(name):
    # usuń plik zdjęcia
    os.remove(os.path.join('static', name + '.jpg'))

    # usuń tabelę z bazy danych
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(f'DROP TABLE {name}')
    c.execute(f'DELETE FROM photos WHERE name = ?', (name,))
    conn.commit()
    conn.close()

    # przekieruj użytkownika na stronę główną
    return redirect(url_for('history'))


@app.route('/losowanie/<name>', methods=['POST'])
def losowanie(name):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    data = request.form.to_dict()
    ilosc = int(data.get('ilosc'))

    c.execute(f'SELECT losy, path FROM {name}')
    losy = [(row[0], row[1]) for row in c.fetchall()]

    if ilosc > len(losy):
        return "Nie można wylosować więcej osób niż jest w puli."

    zwyciezcy = set()
    while len(zwyciezcy) < ilosc:
        zwyciezca, path = random.choice(losy)
        if zwyciezca.strip() and zwyciezca not in zwyciezcy:
            zwyciezcy.add(zwyciezca)
            path_to_save = path

    c.execute('''CREATE TABLE IF NOT EXISTS zwyciezcy
                (id INTEGER PRIMARY KEY,
                imie TEXT NOT NULL,
                nagroda TEXT,
                path TEXT)''')
    for zwyciezca in zwyciezcy:
        c.execute(
            "INSERT INTO zwyciezcy (imie, nagroda, path) SELECT ?, ?, ? WHERE NOT EXISTS (SELECT 1 FROM zwyciezcy WHERE imie = ?)",
            (zwyciezca, name, path_to_save, zwyciezca))
    conn.commit()
    conn.close()

    # usuń tabelę z bazy danych
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(f'DROP TABLE {name}')
    c.execute(f'DELETE FROM photos WHERE name = ?', (name,))
    conn.commit()
    conn.close()

    return redirect(url_for('history'))


@app.route('/wyniki')
def wyniki():
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM zwyciezcy")
    zwyciezcy = c.fetchall()
    conn.close()
    return render_template('wyniki.html', zwyciezcy=zwyciezcy)

if __name__ == '__main__':
    app.run(debug=True)