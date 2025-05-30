import os
import sqlite3
from flask import Flask, redirect, request, session
from jinja2 import Template

app = Flask(__name__)
app.secret_key = 'sqlinjection'
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database.db')


def connect_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS user(
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT    NOT NULL UNIQUE,
                password TEXT    NOT NULL
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS time_line(
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                content  TEXT    NOT NULL,
                FOREIGN KEY(user_id) REFERENCES user(id)
            )
        ''')
        conn.commit()


def init_data():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.executemany(
            'INSERT OR IGNORE INTO user(username, password) VALUES (?,?)',
            [('alice', 'alicepw'), ('bob', 'bobpw')]
        )
        cur.executemany(
            'INSERT OR IGNORE INTO time_line(user_id, content) VALUES (?,?)',
            [(1, 'Hello world'), (2, 'Hi there')]
        )
        conn.commit()


def authenticate(username, password):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute(
            'SELECT id, username FROM user WHERE username=? AND password=?',
            (username, password)
        )
        row = cur.fetchone()
        return dict(row) if row else None


def create_time_line(uid, content):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO time_line(user_id, content) VALUES (?,?)',
            (uid, content)
        )
        conn.commit()


def get_time_lines():
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute('SELECT id, user_id, content FROM time_line ORDER BY id DESC')
        return [dict(r) for r in cur.fetchall()]


def delete_time_line(uid, tid):
    with connect_db() as conn:
        cur = conn.cursor()
        cur.execute(
            'DELETE FROM time_line WHERE user_id=? AND id=?',
            (uid, tid)
        )
        conn.commit()


@app.route('/search')
def search():
    keyword = request.args.get('keyword', '')
    conn = connect_db()
    cur = conn.cursor()

    query = f"SELECT id, user_id, content FROM time_line WHERE content LIKE '%{keyword}%'"
    cur.execute(query)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()

    return Template('''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Search Result</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.4.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
  <div class="container mt-5">
    <h2>Search Result for "<span class="text-primary">{{ keyword }}</span>"</h2>
    <a href="/" class="btn btn-secondary btn-sm mb-3">Back</a>

    {% if results %}
      <div class="card">
        <ul class="list-group list-group-flush">
          {% for item in results %}
          <li class="list-group-item">
            <strong>Timeline ID:</strong> {{ item.id }}<br>
            <strong>User ID:</strong> {{ item.user_id }}<br>
            <strong>Content:</strong> {{ item.content }}
          </li>
          {% endfor %}
        </ul>
      </div>
    {% else %}
      <div class="alert alert-warning mt-3">No results found.</div>
    {% endif %}

    <form action="/search" method="get" class="mt-4 input-group">
      <input name="keyword" class="form-control" placeholder="Search again..." value="{{ keyword }}">
      <button class="btn btn-outline-secondary" type="submit">Search</button>
    </form>
  </div>
</body>
</html>
    ''').render(keyword=keyword, results=rows)


@app.route('/init')
def init_page():
    create_tables()
    init_data()
    return redirect('/')


@app.route('/')
def index():
    if 'uid' in session:
        tl = get_time_lines()
        return Template('''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Dashboard</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.4.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
  <nav class="navbar navbar-dark bg-primary mb-4 p-3">
    <span class="navbar-brand">Timeline App</span>
    <span class="text-white">Welcome, {{ user }}</span>
    <a class="btn btn-light" href="/logout">Logout</a>
  </nav>

  <div class="container">
    <h5 class="mb-3">Add New Timeline</h5>
    <form action="/create" method="post" class="d-flex mb-4">
      <input name="content" class="form-control me-2" placeholder="Add new entry..." required>
      <button type="submit" class="btn btn-success">Add</button>
    </form>

    <div class="card mb-3">
      <div class="card-header">Timeline</div>
      <ul class="list-group list-group-flush">
        {% for line in tl %}
        <li class="list-group-item d-flex justify-content-between align-items-center">
          {{ line.content }}
          <a href="/delete/{{ line.id }}" class="btn btn-danger btn-sm">Delete</a>
        </li>
        {% else %}
        <li class="list-group-item text-muted text-center">No entries yet.</li>
        {% endfor %}
      </ul>
    </div>
  </div>

  <!-- JavaScript payload simulation -->
  <script>
    console.log("YOU HAVE BEEN INFECTED HAHAHA!!!");
  </script>
</body>
</html>
        ''').render(user=session['username'], tl=tl)
    return redirect('/login')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = authenticate(request.form['username'], request.form['password'])
        if user:
            session['uid'] = user['id']
            session['username'] = user['username']
            return redirect('/')
    return '''
<form method="post">
  <input name="username" placeholder="user"/>
  <input name="password" type="password"/>
  <button>Login</button>
</form>
'''


@app.route('/create', methods=['POST'])
def create():
    if 'uid' in session:
        create_time_line(session['uid'], request.form['content'])
    return redirect('/')


@app.route('/delete/<int:tid>')
def delete(tid):
    if 'uid' in session:
        delete_time_line(session['uid'], tid)
    return redirect('/')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


if __name__ == '__main__':
    app.run(debug=True)
