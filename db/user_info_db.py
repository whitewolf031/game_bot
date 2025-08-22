from datetime import datetime, date
import psycopg2
from config import Config

cfg = Config()

class User_info:
    def __init__(self):
        self.connect = psycopg2.connect(
            host=cfg.host,
            user=cfg.user,
            database=cfg.db,
            password=cfg.password
        )
        self.cursor = self.connect.cursor()
        self.create_tables()

    def create_tables(self):
        # Users table
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

        # Chess games table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS chess_games (
                id SERIAL PRIMARY KEY,
                game_id TEXT NOT NULL UNIQUE,
                player1_id BIGINT NOT NULL,
                player2_id BIGINT,
                player1_color TEXT NOT NULL,
                player2_color TEXT,
                moves TEXT[],
                winner_id BIGINT,
                status TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                finished_at TIMESTAMP
            );
        """)

        self.connect.commit()
        print("Tables created")

    def insert_or_update_user_daily(self, chat_id, username, is_admin=False):
        # ... (keep your existing implementation)
        pass

    def select_info(self, chat_id):
        # ... (keep your existing implementation)
        pass

    def add_points_to_user(self, user_id, points):
        self.cursor.execute("""
            UPDATE users
            SET points = points + %s
            WHERE chat_id = %s
            RETURNING points
        """, (points, user_id))
        new_points = self.cursor.fetchone()[0]
        self.connect.commit()
        return new_points

    def create_chess_game(self, game_id, player1_id, player1_color='white'):
        self.cursor.execute("""
            INSERT INTO chess_games (game_id, player1_id, player1_color, status, created_at)
            VALUES (%s, %s, %s, 'waiting', %s)
        """, (game_id, player1_id, player1_color, datetime.now()))
        self.connect.commit()

    def join_chess_game(self, game_id, player2_id):
        self.cursor.execute("""
            UPDATE chess_games
            SET player2_id = %s,
                player2_color = CASE WHEN player1_color = 'white' THEN 'black' ELSE 'white' END,
                status = 'active'
            WHERE game_id = %s
        """, (player2_id, game_id))
        self.connect.commit()

    def record_chess_move(self, game_id, move):
        self.cursor.execute("""
            UPDATE chess_games
            SET moves = array_append(moves, %s)
            WHERE game_id = %s
        """, (move, game_id))
        self.connect.commit()

    def end_chess_game(self, game_id, winner_id):
        self.cursor.execute("""
            UPDATE chess_games
            SET winner_id = %s,
                status = 'finished',
                finished_at = %s
            WHERE game_id = %s
        """, (winner_id, datetime.now(), game_id))
        self.connect.commit()

    def get_user_games(self, user_id):
        self.cursor.execute("""
            SELECT game_id, player1_id, player2_id, status, winner_id, created_at
            FROM chess_games
            WHERE player1_id = %s OR player2_id = %s
            ORDER BY created_at DESC
        """, (user_id, user_id))
        return self.cursor.fetchall()

    def create_shashka_game(self, game_id, player1_id, player1_color='white'):
        self.cursor.execute("""
            INSERT INTO shashka_games (game_id, player1_id, player1_color, status, created_at)
            VALUES (%s, %s, %s, 'waiting', %s)
        """, (game_id, player1_id, player1_color, datetime.now()))
        self.connect.commit()

    def join_shashka_game(self, game_id, player2_id):
        self.cursor.execute("""
            UPDATE shashka_games
            SET player2_id = %s,
                player2_color = CASE WHEN player1_color = 'white' THEN 'black' ELSE 'white' END,
                status = 'active'
            WHERE game_id = %s
        """, (player2_id, game_id))
        self.connect.commit()

    def record_shashka_move(self, game_id, move):
        self.cursor.execute("""
            UPDATE shashka_games
            SET moves = array_append(moves, %s)
            WHERE game_id = %s
        """, (move, game_id))
        self.connect.commit()

    def end_shashka_game(self, game_id, winner_id):
        self.cursor.execute("""
            UPDATE shashka_games
            SET winner_id = %s,
                status = 'finished',
                finished_at = %s
            WHERE game_id = %s
        """, (winner_id, datetime.now(), game_id))
        self.connect.commit()

    def get_user_shashka_games(self, user_id):
        self.cursor.execute("""
            SELECT game_id, player1_id, player2_id, status, winner_id, created_at
            FROM shashka_games
            WHERE player1_id = %s OR player2_id = %s
            ORDER BY created_at DESC
        """, (user_id, user_id))
        return self.cursor.fetchall()