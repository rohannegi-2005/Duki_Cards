# firebase_service.py

import firebase_admin
from firebase_admin import credentials, db

# Init only once
if not firebase_admin._apps:
    cred = credentials.Certificate("D:\\Card_game\\cards-game-47ef7-firebase-adminsdk-fbsvc-d59b5c75fc.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://cards-game-47ef7-default-rtdb.firebaseio.com/'
    })

def create_room(room_code, data):
    db.reference(f"games/{room_code}").set(data)

def join_room(room_code, player_id, player_data):
    db.reference(f"games/{room_code}/players/{player_id}").set(player_data)

def get_game(room_code):
    return db.reference(f"games/{room_code}").get()

def update_game_field(room_code, field_path, value):
    db.reference(f"games/{room_code}/{field_path}").set(value)

def update_player_hand(room_code, player_id, new_hand):
    db.reference(f"games/{room_code}/players/{player_id}/hand").set(new_hand)

def mark_player_pass(room_code, player_id, status=True):
    db.reference(f"games/{room_code}/players/{player_id}/passed").set(status)

def delete_room(room_code):
    db.reference(f"games/{room_code}").delete()
