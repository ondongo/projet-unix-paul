
from dataclasses import dataclass
from flask import Flask, request, redirect, make_response
from datetime import datetime, timezone

app = Flask(__name__)


@dataclass
class User:
    username: str
    password: str


USERS = {
    "paul": User("paul", "paul2026"),
    "linux": User("linux", "linux123"),
    "princedegloire": User("princedegloire", "Azerty0000@"),
}


COOKIE_NAME = "auth"
COOKIE_VALUE = "ok"
LOG_FILE = "/var/log/authapp.log"


def log_failed_login(ip, username):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"FAILED_LOGIN ip={ip} user={username} time={now}\n"
    with open(LOG_FILE, "a") as f:
        f.write(line)

def is_authenticated(req):
    return req.cookies.get(COOKIE_NAME) == COOKIE_VALUE

@app.get("/")
def index():
    return "OK", 200

@app.get("/login")
def login_form():
    return """
    <h1>Login</h1>
    <form method="POST" action="/login">
        <input name="username" placeholder="Username">
        <input name="password" type="password" placeholder="Password">
        <button type="submit">Connexion</button>
    </form>
    """

@app.post("/login")
def login():
    username = request.form.get("username")
    password = request.form.get("password")

    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    user = USERS.get(username)
    if not user or user.password != password:
        log_failed_login(ip, username)
        return "Unauthorized", 401
    response = make_response(redirect("/private"))
    response.set_cookie(COOKIE_NAME, COOKIE_VALUE)
    return response

@app.get("/private")
def private():
    if not is_authenticated(request):
        return "Unauthorized", 401
    return "Accès au contenu privé autorisé", 200