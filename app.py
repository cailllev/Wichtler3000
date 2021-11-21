from flask import Flask, render_template, request, redirect, url_for, session
from secrets import token_bytes

from db import check_login, create_group, delete_group, draw_group, join_group, get_to_gift, get_group_members, \
    leave_group, register_user

app = Flask(__name__)
app.secret_key = token_bytes(16)


@app.route("/", methods=["GET"])
def index():
    if "username" in session:
        return render_template("index.html", user=session["username"])
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        print("APP", username, password)
        if register_user(username, password):
            session["username"] = username
            return render_template("index.html", user=username)
        return render_template("register.html", message="User already exists. Choose another username.")

    if request.method == "GET":
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if check_login(username, password):
            session["username"] = username
            return render_template("index.html", user=username)
        else:
            return render_template("login.html", message="Wrong username or password")

    if request.method == "GET":
        return render_template("login.html")


@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))


@app.route("/groups", methods=["GET", "POST", "DELETE"])
def groups():
    if "username" not in session:
        return render_template("login.html", message="Please log in.")

    if request.method == "POST":
        group_name = request.form["name"]
        group_pw = request.form["password"]
        if create_group(group_name, group_pw, session["username"]):
            return render_template("groups.html", message=f"Successfully created group {group_name}")
        return render_template("groups.html", message=f"Group {group_name} already exists.")

    if request.method == "DELETE":
        group_name = request.args.get("group")
        if delete_group(group_name, session["username"]):
            return render_template("groups.html", message=f"Group {group_name} successfully deleted.")
        return render_template("groups.html", message="Only the creator can delete the group.")

    if request.method == "GET":
        return render_template("groups.html")


@app.route("/group/:group_name", methods=["GET", "POST", "DELETE"])
def group_member():
    if "username" not in session:
        return render_template("login.html", message="Please log in.")

    if request.method == "POST":
        group_name = request.form["name"]
        group_pw = request.form["password"]
        if join_group(group_name, group_pw, session["username"]):
            return render_template("groups", message=f"Successfully joined {group_name}")
        return render_template("groups", message=f"Unable to join {group_name}")

    if request.method == "DELETE":
        group_name = request.args.get("name")
        leave_group(group_name, session["username"])
        return render_template("groups", message=f"Successfully left {group_name}")

    if request.method == "GET":
        group_name = request.args.get("name")
        to_gift = get_to_gift(group_name, session["username"])
        members = get_group_members(group_name, session["username"])
        return render_template("group.html", message="", members=members, to_gift=to_gift)


@app.route("/group/:group_name/draw", methods=["GET"])
def draw_group():
    group_name = request.args.get("name")
    user = session["username"]
    members = get_group_members(group_name, session["username"])
    if draw_group(group_name, user):
        return render_template("group.html", message="Drew group.", members=members)
    return render_template("group.html", message=f"Unauthorized to draw group {group_name}", members=[""], to_gift="")


@app.errorhandler(500)
def internal_error():
    return render_template("error.html")


# FLASK_APP=app.py FLASK_ENV=development flask run --port 8080
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9001)
