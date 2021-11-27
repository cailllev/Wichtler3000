from flask import Flask, render_template, request, redirect, session
from secrets import token_bytes

from db import check_login, create_group, draw_group, join_group, get_to_gift, get_in_groups, \
    get_creator_and_drawn, get_group_members, group_exists, leave_group, register_user

app = Flask(__name__)
app.secret_key = token_bytes(16)
USER = "username"


@app.route("/", methods=["GET"])
def index():
    if USER in session:
        in_groups = get_in_groups(session[USER])
        return render_template("index.html", user=session[USER], groups=in_groups)
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form[USER]
        password = request.form["password"]
        if register_user(username, password):
            session[USER] = username
            return render_template("index.html", user=username)
        return render_template("register.html", message="User already exists, choose another username")

    if request.method == "GET":
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form[USER]
        password = request.form["password"]
        if check_login(username, password):
            session[USER] = username
            return redirect("/")
        else:
            return render_template("login.html", message="Wrong username or password")

    if request.method == "GET":
        return render_template("login.html")


@app.route("/logout", methods=["GET"])
def logout():
    session.pop(USER, None)
    return redirect("/")


@app.route("/groups", methods=["GET"])
def groups():
    if USER not in session:
        return render_template("login.html", message="Please log in.")

    in_groups = get_in_groups(session[USER])
    return render_template("groups.html", message="Create or join a group", groups=in_groups)


@app.route("/groups/create", methods=["POST"])
def group_create():
    if USER not in session:
        return render_template("login.html", message="Please log in.")

    in_groups = get_in_groups(session[USER])
    group_name = request.form["name"]
    group_pw = request.form["password"]
    if create_group(group_name, group_pw, session[USER]):
        return render_template(
            "groups.html",
            message=f"Successfully created group: {group_name}",
            groups=in_groups.append(group_name)
        )

    return render_template(
        "groups.html",
        message=f"Group already exists: {group_name}",
        groups=in_groups
    )


@app.route("/groups/join", methods=["POST"])
def group_join():
    if USER not in session:
        return render_template("login.html", message="Please log in.")

    in_groups = get_in_groups(session[USER])
    if request.method == "POST":
        group_name = request.form["name"]
        group_pw = request.form["password"]
        if join_group(group_name, group_pw, session[USER]):
            return redirect("/groups/"+group_name)
        return render_template("groups.html", message=f"Unable to join: {group_name}", groups=in_groups)


def render_group_info(group_name, user):
    creator, _ = get_creator_and_drawn(group_name)
    return render_template(
        "group.html",
        group_name=group_name,
        message="",
        members=get_group_members(group_name, user),
        to_gift=get_to_gift(group_name, user),
        is_creator=(user == creator)
    )


@app.route("/groups/<group_name>", methods=["GET", "DELETE"])
def group(group_name: str):
    if USER not in session:
        return render_template("login.html", message="Please log in.")

    print("in group", group_name, request.method)
    if request.method == "DELETE":
        print("in leave group", group_name)
        leave_group(group_name, session[USER])
        in_groups = get_in_groups(session[USER])
        return render_template(
            "groups.html",
            message=f"Left group: {group_name}",
            groups=in_groups
        )

    if request.method == "GET":
        if not group_exists(group_name):
            return render_template(
                "groups.html",
                message=f"Group not found: {group_name}",
                groups=get_in_groups(session[USER])
            )
        return render_group_info(group_name, session[USER])


@app.route("/groups/<group_name>/draw", methods=["GET"])
def group_draw(group_name: str):
    if USER not in session:
        return render_template("login.html", message="Please log in.")

    if draw_group(group_name, session[USER]):
        return render_group_info(group_name, session[USER])


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("error.html"), 500


# FLASK_APP=app.py FLASK_ENV=development flask run --port 9001
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=9001)
