'''
Created on 16/oct/2016

@author: Gian Paolo Jesi
'''

"""
Static methods to manage DB.
"""

import sqlite3
import logging as log


def connect_db(file_name):
    """Connect to the specified filename representing the SQLite db.

    :param file_name: db filename
    :return: a pair: (db handler, cursor handler)
    """
    db = sqlite3.connect(file_name)
    c = db.cursor()
    return db, c


def get_userids(cursor, having_treatment=None):
    """Gets all users having a specific treatment. Return a list of unique ids.
    """
    cursor.execute('SELECT id FROM users WHERE treatment=?', (having_treatment,))
    return cursor.fetchall()


def inject_user(dbConn, uid, username):
    """
    Inject a new user if it is not already existent.

    :return: none
    """
    try:
        with dbConn:
            pars = (uid, username)
            print "pars: ", pars
            dbConn.execute(
                """INSERT OR IGNORE INTO users(uid, username) VALUES(?, ?)""", pars)

    except sqlite3.IntegrityError as e:
        log.error("Error in DB transaction when injecting user: ", uid)


def inject_session(dbConn, session_obj):
    try:
        with dbConn:
            pars = (session_obj.uid, session_obj.type, session_obj.ts_start)
            print "pars: ", pars
            dbConn.execute(
                """INSERT OR IGNORE INTO sessions(sid, uid, type, start, end) VALUES(
                null,?,?,?, "YYYY-MM-DD 00:00:00.000")""", pars)

    except sqlite3.IntegrityError as e:
        log.error("Error in DB transaction when injecting session for user: ", session_obj.uid)


def inject_move(dbConn, uid, sid, move, ts):
    try:
        with dbConn:
            pars = (int(uid), int(sid), move, ts)
            print "pars: ", pars
            dbConn.execute(
                """INSERT INTO moves(mid, uid, sid, move, ts) VALUES(null,?,?,?,?)""", pars)

    except sqlite3.IntegrityError as e:
        log.error("Error in DB transaction when injecting user: ", uid)


def make_notification_update(dbConn, obj):
    """
    Make an update for entry in 'notifications' DB table for a notification message.
    When a notification arrives.
    :param dbConn: connection active to DB
    :param obj: decoded json payload as python dict
    :return:
    """
    try:
        with dbConn:
            dbConn.execute("update notifications set rcv_ts=? where msg_id=?",
                           (obj['dt'], obj['msg_id']))

    except sqlite3.IntegrityError as e:
        log.error("Error in DB transaction when updating notification for msg_id: ", obj['msg_id'])


def get_last_uid(cursor):
    """
    Get the last used uid. Corresponds to the number of current rows in users table.

    :param cursor: db cursor
    :return: the number of rows (integer)
    """
    cursor.execute('SELECT count(uid) FROM users')
    return int(cursor.fetchall()[0][0])


def get_last_sid(cursor):
    """
    Get the last sessios id. Corresponds to the number of current rows in sessions table.

    :param cursor: db cursor
    :return: the number of rows (integer)
    """
    cursor.execute('SELECT count(sid) FROM sessions')
    return int(cursor.fetchall()[0][0])


def reset_db(dbConn):
    try:
        with dbConn:
            dbConn.execute("delete from notifications")

    except sqlite3.IntegrityError as e:
        log.error("Error in DB transaction: cannot reset the 'notification' table")


if __name__ == '__main__':
    pass
