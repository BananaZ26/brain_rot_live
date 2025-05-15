from flask import Flask, render_template, redirect, request, session, flash
from werkzeug.utils import secure_filename
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'secret'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Инициализация базы данных
def init_db():
    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            nickname TEXT,
            password TEXT,
            profile_pic TEXT DEFAULT 'default.png'
        )
        ''')

        cur.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            content TEXT,
            image TEXT,
            likes INTEGER DEFAULT 0,
            dislikes INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')

        cur.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            user_id INTEGER,
            post_id INTEGER,
            vote TEXT,
            PRIMARY KEY (user_id, post_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(post_id) REFERENCES posts(id)
        )
        ''')
        con.commit()

init_db()

@app.route('/')
def index():
    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute('''
        SELECT posts.id, posts.content, posts.image, posts.likes, posts.dislikes,
               users.nickname, users.profile_pic
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.id DESC
        ''')
        posts = cur.fetchall()

        cur.execute('''
        SELECT posts.id, posts.content, posts.image, posts.likes,
               users.nickname
        FROM posts
        JOIN users ON posts.user_id = users.id
        ORDER BY posts.likes DESC
        LIMIT 3
        ''')
        top_posts = cur.fetchall()

    return render_template('index.html', posts=posts, top_posts=top_posts)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        nickname = request.form['nickname']
        password = request.form['password']
        with sqlite3.connect('database.db') as con:
            cur = con.cursor()
            try:
                cur.execute("INSERT INTO users (username, nickname, password) VALUES (?, ?, ?)",
                            (username, nickname, password))
                con.commit()
                flash('Регистрация успешна!')
                return redirect('/login')
            except:
                flash('Имя пользователя занято.')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect('database.db') as con:
            cur = con.cursor()
            cur.execute("SELECT id FROM users WHERE username=? AND password=?", (username, password))
            user = cur.fetchone()
            if user:
                session['user_id'] = user[0]
                return redirect('/')
            else:
                flash('Неверные данные.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect('/')

@app.route('/post', methods=['GET', 'POST'])
def post():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        content = request.form['content']
        image_file = request.files['image']
        filename = None
        if image_file and image_file.filename:
            filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        with sqlite3.connect('database.db') as con:
            cur = con.cursor()
            cur.execute("INSERT INTO posts (user_id, content, image) VALUES (?, ?, ?)",
                        (session['user_id'], content, filename))
            con.commit()
        return redirect('/')

    return render_template('post.html')

@app.route('/like/<int:post_id>')
def like(post_id):
    if 'user_id' not in session:
        return redirect('/login')

    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute("SELECT vote FROM votes WHERE user_id=? AND post_id=?", (session['user_id'], post_id))
        existing_vote = cur.fetchone()

        if not existing_vote:
            cur.execute("INSERT INTO votes (user_id, post_id, vote) VALUES (?, ?, ?)",
                        (session['user_id'], post_id, 'like'))
            cur.execute("UPDATE posts SET likes = likes + 1 WHERE id = ?", (post_id,))
        elif existing_vote[0] == 'dislike':
            cur.execute("UPDATE votes SET vote = 'like' WHERE user_id=? AND post_id=?",
                        (session['user_id'], post_id))
            cur.execute("UPDATE posts SET dislikes = dislikes - 1, likes = likes + 1 WHERE id = ?", (post_id,))
        con.commit()
    return redirect('/')

@app.route('/dislike/<int:post_id>')
def dislike(post_id):
    if 'user_id' not in session:
        return redirect('/login')

    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute("SELECT vote FROM votes WHERE user_id=? AND post_id=?", (session['user_id'], post_id))
        existing_vote = cur.fetchone()

        if not existing_vote:
            cur.execute("INSERT INTO votes (user_id, post_id, vote) VALUES (?, ?, ?)",
                        (session['user_id'], post_id, 'dislike'))
            cur.execute("UPDATE posts SET dislikes = dislikes + 1 WHERE id = ?", (post_id,))
        elif existing_vote[0] == 'like':
            cur.execute("UPDATE votes SET vote = 'dislike' WHERE user_id=? AND post_id=?",
                        (session['user_id'], post_id))
            cur.execute("UPDATE posts SET likes = likes - 1, dislikes = dislikes + 1 WHERE id = ?", (post_id,))
        con.commit()
    return redirect('/')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        nickname = request.form['nickname']
        profile_pic = request.files['profile_pic']
        filename = None
        if profile_pic and profile_pic.filename:
            filename = secure_filename(profile_pic.filename)
            profile_pic.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            with sqlite3.connect('database.db') as con:
                cur = con.cursor()
                cur.execute("UPDATE users SET nickname=?, profile_pic=? WHERE id=?",
                            (nickname, filename, session['user_id']))
        else:
            with sqlite3.connect('database.db') as con:
                cur = con.cursor()
                cur.execute("UPDATE users SET nickname=? WHERE id=?", (nickname, session['user_id']))
        return redirect('/profile')

    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute("SELECT nickname, profile_pic FROM users WHERE id=?", (session['user_id'],))
        user = cur.fetchone()
        cur.execute("SELECT content, image, likes, dislikes FROM posts WHERE user_id=?",
                    (session['user_id'],))
        posts = cur.fetchall()

    return render_template('profile.html', user=user, posts=posts)

if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
