import sqlite3
from hashlib import pbkdf2_hmac
from random import shuffle
from secrets import token_bytes
from typing import List

pepper = b"mUcH_P3pPeR:SuCH W0w!"


def init() -> None:
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            name VARCHAR UNIQUE, 
            salt VARCHAR,
            hash VARCHAR
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            name    VARCHAR UNIQUE,
            creator VARCHAR,
            salt    VARCHAR,
            hash    VARCHAR,
            drawn   INTEGER,
            FOREIGN KEY (creator)
                REFERENCES users (name)
        )""")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            member     VARCHAR,
            to_gift    VARCHAR,
            group_name VARCHAR,
            FOREIGN KEY (member)
                REFERENCES users (name),
            FOREIGN KEY (to_gift)
                REFERENCES users (name),
            FOREIGN KEY (group_name)
                REFERENCES groups (name)
        )""")
        con.commit()


# ********** USER LOGIN ********** #
def pw_hash(password: str, salt: bytes):
    return pbkdf2_hmac("sha256", password.encode() + pepper, salt, 2**16).hex()


def register_user(username: str, password: str) -> bool:
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE name = (?)", (username, ))
        rows = cur.fetchall()
        if rows:
            return False

        salt = token_bytes(32)
        hashed = pw_hash(password, salt)
        hex_salt = salt.hex()

        cur.execute("INSERT INTO users VALUES (?, ?, ?)", (username, hex_salt, hashed))
        con.commit()
        return True


def check_login(username: str, password: str) -> bool:
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT salt, hash FROM users WHERE name = (?)", (username, ))
        row = cur.fetchone()
        if not row:
            return False

        hex_salt, hashed = row
        salt = bytes.fromhex(hex_salt)
        if hashed == pw_hash(password, salt):
            return True
        return False


# ********** GROUPS ********** #
def group_exists(group_name: str) -> bool:
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM groups WHERE name = (?)", (group_name, ))
        row = cur.fetchone()
        if row:
            return True
    return False


def create_group(group_name: str, group_pw: str, creator: str) -> bool:
    if group_exists(group_name):
        return False

    with sqlite3.connect("database.db") as con:
        salt = token_bytes(32)
        hashed = pw_hash(group_pw, salt)
        hex_salt = salt.hex()

        cur = con.cursor()
        cur.execute("INSERT INTO groups VALUES (?, ?, ?, ?, ?)", (group_name, creator, hex_salt, hashed, 0))
        cur.execute("INSERT INTO group_members VALUES (?, ?, ?)", (creator, "", group_name))
        con.commit()
    return True


def join_group(group_name: str, group_password: str, user: str) -> bool:
    if not group_exists(group_name) or user_in_group(group_name, user):
        return False

    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT salt, hash FROM groups WHERE name = (?)", (group_name,))
        row = cur.fetchone()
        if not row:
            return False

        hex_salt, hashed = row
        salt = bytes.fromhex(hex_salt)
        if hashed == pw_hash(group_password, salt):
            cur.execute("INSERT INTO group_members VALUES (?, ?, ?)", (user, "", group_name))
            con.commit()
            return True
        return False


def leave_group(group_name: str, user: str) -> None:
    if not group_exists(group_name) or not user_in_group(group_name, user):
        return

    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("DELETE FROM group_members WHERE member = (?) AND group_name = (?)", (user, group_name))

        cur.execute("SELECT * FROM group_members WHERE group_name = (?)", (group_name,))
        row = cur.fetchone()

        # delete group if no members left
        if not row:
            cur.execute("DELETE FROM groups WHERE name = (?)", (group_name,))
        # delete draws
        else:
            cur.execute("UPDATE groups SET drawn = 0 WHERE name = (?)", (group_name,))
            cur.execute("UPDATE group_members SET to_gift = ''")

        con.commit()


def draw_group(group_name: str, user: str) -> bool:
    if not group_exists(group_name):
        return False

    creator, drawn = get_creator_and_drawn(group_name)
    if creator != user:
        return False
    if drawn:
        return False

    with sqlite3.connect("database.db") as con:
        cur = con.cursor()

        cur.execute("UPDATE groups SET drawn = 1 WHERE name = (?)", (group_name, ))
        users = get_group_members(group_name, user)
        shuffle(users)

        for i in range(len(users)):
            gifter = users[i]
            to_gift = users[i-1]
            cur.execute("UPDATE group_members SET to_gift = (?) WHERE group_name = (?) AND member = (?)",
                        (to_gift, group_name, gifter))

        con.commit()
        return True


def user_in_group(group_name: str, user: str) -> bool:
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM group_members WHERE group_name = (?) and member = (?)", (group_name, user))
        row = cur.fetchone()
        if row:
            return True
        return False


def get_creator_and_drawn(group_name: str) -> [str, str]:
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT creator, drawn FROM groups WHERE name = (?)", (group_name, ))
        row = cur.fetchone()
        if not row:
            return "", ""
        return row


def get_to_gift(group_name: str, user: str) -> str:
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT to_gift FROM group_members WHERE group_name = (?) AND member = (?)", (group_name, user))
        row = cur.fetchone()
        if not row:
            return ""
        return row[0]


def get_group_members(group_name: str, user: str) -> List[str]:
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT member FROM group_members WHERE group_name = (?)", (group_name,))
        rows = cur.fetchall()
        if not rows:
            return [""]

        users = [row[0] for row in rows]
        if user not in users:
            return [""]
        return users


def get_in_groups(user: str) -> List[str]:
    with sqlite3.connect("database.db") as con:
        cur = con.cursor()
        cur.execute("SELECT group_name FROM group_members WHERE member = (?)", (user,))
        rows = cur.fetchall()
        if not rows:
            return []
        groups = [row[0] for row in rows]
        return groups


init()
