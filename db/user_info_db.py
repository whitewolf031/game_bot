from datetime import datetime, date

import psycopg2

class User_info:
    def __init__(self):
        self.connect = psycopg2.connect(
            host="localhost",
            user="postgres",
            password="Jahongir2004#",
            database="choice_info"
        )
        self.cursor = self.connect.cursor()
        self.create_user_table()

    def create_user_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                chat_id BIGINT NOT NULL UNIQUE,
                username TEXT,
                points INTEGER DEFAULT 0,
                last_daily TIMESTAMP,
                is_admin BOOLEAN DEFAULT FALSE,
                referred_by BIGINT
            );
            """)

        self.connect.commit()
        print("Table created")

    def insert_into_users(self, chat_id, username, points, last_daily, is_admin):
        self.cursor.execute("""
            INSERT INTO users (chat_id, username, points, last_daily, is_admin)
            VALUES (%s, %s, %s, %s, %s)
        """, (chat_id, username, points, last_daily, is_admin))
        self.connect.commit()

    def insert_or_update_user_daily(self, chat_id, username, is_admin=False):
        self.cursor.execute("SELECT points, last_daily FROM users WHERE chat_id = %s", (chat_id,))
        result = self.cursor.fetchone()

        if result:
            points, last_daily = result
            # Har kuni bir martalik ball
            if last_daily is None or last_daily.date() < date.today():
                points += 1
                self.cursor.execute("""
                    UPDATE users 
                    SET points = %s, last_daily = %s, username = %s
                    WHERE chat_id = %s
                """, (points, datetime.now(), username, chat_id))
            is_new = False
        else:
            self.cursor.execute("""
                INSERT INTO users (chat_id, username, points, last_daily, is_admin)
                VALUES (%s, %s, %s, %s, %s)
            """, (chat_id, username, 1, datetime.now(), is_admin))
            is_new = True

        self.connect.commit()
        return is_new

    def select_info(self, chat_id):
        self.cursor.execute("""
            SELECT id, username, points, last_daily, is_admin
            FROM users
            WHERE chat_id = %s
        """, (chat_id,))
        print("Ma'lumot olindi")
        return self.cursor.fetchall()

    def add_points_to_user(self, user_id, bonus=10):
        self.cursor.execute("""
            UPDATE users
            SET points = points + %s
            WHERE chat_id = %s
        """, (bonus, user_id))
        self.connect.commit()


User = User_info()
