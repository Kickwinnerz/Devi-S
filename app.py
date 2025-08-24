from flask import Flask, render_template, request, redirect, url_for, session
import os, sqlite3
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "supersecret"  # change for production

# Uploads config
UPLOAD_FOLDER = "static/uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "mp4", "mov"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Database setup
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
                    id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE,
                    password TEXT
                 )""")
    c.execute("""CREATE TABLE IF NOT EXISTS posts(
                    id INTEGER PRIMARY KEY,
                    user TEXT,
                    content TEXT,
                    filename TEXT,
                    likes INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0
                 )""")
    c.execute("""CREATE TABLE IF NOT EXISTS comments(
                    id INTEGER PRIMARY KEY,
                    post_id INTEGER,
                    user TEXT,
                    comment TEXT
                 )""")
    conn.commit()
    conn.close()

@app.route("/")
def index():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, user, content, filename, likes, views FROM posts ORDER BY id DESC")
    posts = c.fetchall()
    c.execute("SELECT id, post_id, user, comment FROM comments ORDER BY id ASC")
    comments = c.fetchall()
    conn.close()
    return render_template("index.html", posts=posts, comments=comments)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        if not username or not password:
            return render_template("signup.html", error="Fill all fields")
        try:
            conn = sqlite3.connect("database.db")
            c = conn.cursor()
            c.execute("INSERT INTO users(username, password) VALUES(?, ?)", (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("signup.html", error="Username already exists")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session["username"] = username
            return redirect(url_for("index"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/post", methods=["POST"])
def post():
    if "username" not in session:
        return redirect(url_for("login"))

    content = request.form.get("content", "").strip()
    file = request.files.get("file")
    filename = None

    if file and file.filename != "" and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        # ensure unique filename if exists
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(save_path):
            filename = f"{base}_{counter}{ext}"
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            counter += 1
        file.save(save_path)

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("INSERT INTO posts(user, content, filename) VALUES(?, ?, ?)",
              (session["username"], content, filename))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/profile")
def profile():
    if "username" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, content, filename, likes, views FROM posts WHERE user=? ORDER BY id DESC", (session["username"],))
    myposts = c.fetchall()
    conn.close()
    return render_template("profile.html", username=session["username"], posts=myposts)

@app.route("/delete/<int:post_id>")
def delete(post_id):
    if "username" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT filename FROM posts WHERE id=? AND user=?", (post_id, session["username"]))
    post = c.fetchone()
    if post:
        if post[0]:
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], post[0])
            if os.path.exists(filepath):
                os.remove(filepath)
        c.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
        c.execute("DELETE FROM posts WHERE id=? AND user=?", (post_id, session["username"]))
        conn.commit()
    conn.close()
    return redirect(url_for("profile"))

@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
def edit(post_id):
    if "username" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    if request.method == "POST":
        new_content = request.form.get("content", "").strip()
        c.execute("UPDATE posts SET content=? WHERE id=? AND user=?", (new_content, post_id, session["username"]))
        conn.commit()
        conn.close()
        return redirect(url_for("profile"))
    c.execute("SELECT content FROM posts WHERE id=? AND user=?", (post_id, session["username"]))
    post = c.fetchone()
    conn.close()
    if not post:
        return redirect(url_for("profile"))
    return render_template("edit.html", post=post, post_id=post_id)

@app.route("/like/<int:post_id>")
def like(post_id):
    if "username" not in session:
        return redirect(url_for("login"))
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE posts SET likes = likes + 1 WHERE id=?", (post_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/comment/<int:post_id>", methods=["POST"])
def comment(post_id):
    if "username" not in session:
        return redirect(url_for("login"))
    comment_text = request.form.get("comment", "").strip()
    if comment_text:
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO comments(post_id, user, comment) VALUES(?, ?, ?)",
                  (post_id, session["username"], comment_text))
        conn.commit()
        conn.close()
    return redirect(url_for("index"))

@app.route("/view/<int:post_id>")
def view(post_id):
    # Increment views then show feed (or redirect to index)
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE posts SET views = views + 1 WHERE id=?", (post_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)