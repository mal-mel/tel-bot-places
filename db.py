import sqlite3


class DB:
    def __init__(self, db):
        self.con = sqlite3.connect(db, check_same_thread=False)

    def query(self, sql, *args):
        self.con.commit()
        cur = self.con.cursor()
        cur.execute(sql, *args)
        self.con.commit()
        return cur

    def __del__(self):
        self.con.close()
