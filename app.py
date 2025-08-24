from flask import Flask, render_template, request, redirect, url_for, session
import os
from supabase import create_client
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"png","jpg","jpeg","gif","mp4","mov"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".",1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    posts = supabase.table("posts").select("*").order("id",desc=True).execute().data
    comments = supabase.table("comments").select("*").execute().data
    return render_template("index.html", posts=posts, comments=comments)

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method=="POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")
        if not username or not password:
            return render_template("signup.html", error="Fill all fields")
        try:
            supabase.table("users").insert({"username":username,"password":password}).execute()
            return redirect(url_for("login"))
        except:
            return render_template("signup.html", error="Username exists")
    return render_template("signup.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = supabase.table("users").select("*").eq("username",username).eq("password",password).execute().data
        if user:
            session["username"]=username
            return redirect(url_for("index"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("username",None)
    return redirect(url_for("login"))

@app.route("/post", methods=["POST"])
def post():
    if "username" not in session:
        return redirect(url_for("login"))
    content = request.form.get("content","").strip()
    file = request.files.get("file")
    filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        path = os.path.join(UPLOAD_FOLDER, filename)
        counter = 1
        base, ext = os.path.splitext(filename)
        while os.path.exists(path):
            filename = f"{base}_{counter}{ext}"
            path = os.path.join(UPLOAD_FOLDER, filename)
            counter+=1
        file.save(path)
    supabase.table("posts").insert({"user":session["username"],"content":content,"filename":filename}).execute()
    return redirect(url_for("index"))

# Additional routes: profile, edit, delete, like, comment, view
# You can replicate the previous Flask logic but replace sqlite3 with supabase.table() calls

if __name__=="__main__":
    app.run(debug=True)