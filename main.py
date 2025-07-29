from streamlit_autorefresh import st_autorefresh
from firebase_admin import credentials, db, initialize_app
import streamlit as st
import uuid
from firebase import (
    create_room, join_room, get_game, update_game_field,
    update_player_hand, mark_player_pass
)

import time

RANK_ORDER = ['3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A', '2']
st.set_page_config(page_title="Multiplayer Card Game", layout="wide")
st.title("🃏 Multiplayer Card Game")
st_autorefresh(interval=4500, key="refresh")

# --- SESSION STATE INIT ---
for key in ["room_code", "player_id", "player_name", "is_host", "game_started", "selected_cards"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "selected_cards" else []

# --- JOIN OR CREATE ROOM ---
if not st.session_state.room_code:
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎮 Create Game"):
            st.session_state.room_code = str(uuid.uuid4())[:6].upper()
            st.session_state.player_id = str(uuid.uuid4())[:8]
            st.session_state.is_host = True
    with col2:
        join_code = st.text_input("Enter Room Code to Join:")
        if join_code:
            st.session_state.room_code = join_code.upper()
            st.session_state.player_id = str(uuid.uuid4())[:8]
            st.session_state.is_host = False

# --- ENTER NAME ---
if st.session_state.room_code and not st.session_state.player_name:
    st.subheader(f"Room: {st.session_state.room_code}")
    name = st.text_input("Enter your name to join game:")
    if name:
        st.session_state.player_name = name
        join_room(st.session_state.room_code, st.session_state.player_id, {
            "name": name, "hand": [], "passed": False
        })

# --- WAITING ROOM ---
if st.session_state.player_name and not st.session_state.game_started:
    game = get_game(st.session_state.room_code) or {}
    st.subheader(f"👥 Waiting in Room: {st.session_state.room_code}")
    st.write("Players Joined:")
    if "players" in game:
        for p in game["players"].values():
            st.markdown(f"- {p['name']}")

    if st.session_state.is_host and st.button("🚀 Start Game"):
        # Creating a shuffled deck
        import random
        SUITS = ['♣', '♦', '♥', '♠']
        players = list(game["players"].keys())
        deck = []
        for rank in RANK_ORDER:
            for suit in SUITS:
                card = f"{rank}{suit}"
                deck.append(card)
        random.shuffle(deck)

        # Card distribution
        hands = {}
        for pid in players:
            hands[pid] = [] 
            
        i = 0
        for card in deck:
            player_id = players[i]         
            hands[player_id].append(card)   
            i += 1
            if i == len(players):         
                i = 0 
                
        # All players Hand saving to the database...
        for pid, hand in hands.items():
            update_player_hand(st.session_state.room_code, pid, hand)
            
        update_game_field(st.session_state.room_code, "turn_order", players)
        # ✅ Find the player with 3♣ and give first turn
        first_player = None
        for pid, hand in hands.items():
            if '3♣' in hand:
                first_player = pid
                break
        
        if first_player:
            update_game_field(st.session_state.room_code, "current_turn", first_player)
        else:
            update_game_field(st.session_state.room_code, "current_turn", players[0])  # fallback
  
        update_game_field(st.session_state.room_code, "last_played", [])
        update_game_field(st.session_state.room_code, "same_count", 0)
        update_game_field(st.session_state.room_code, "last_player", "")
        update_game_field(st.session_state.room_code, "winner", "")
        st.session_state.game_started = True
        st.rerun()

    if not st.session_state.is_host:
        st.info("Waiting for host to start the game...")

# --- MAIN GAME LOOP ---
if st.session_state.player_name and (st.session_state.game_started or get_game(st.session_state.room_code).get("current_turn")):
    game = get_game(st.session_state.room_code)

    # ✅ First check if the game has a winner
    if game.get("winner"):
        st.balloons()
        st.image("https://media.giphy.com/media/5GoVLqeAOo6PK/giphy.gif")
        st.success(f"🎉 {game['winner']} WINS!")
        st.stop()

    # 🃏 GET CURRENT PLAYER DATA
    player_data = game["players"][st.session_state.player_id]
    hand = sorted(player_data["hand"], key=lambda c: RANK_ORDER.index(c[:-1]))
    valid_selected = []
    current_turn = game["current_turn"]
    last_played = game.get("last_played", [])
    same_count = game.get("same_count", 0)
    last_player = game.get("last_player", "")

    # 👤 Display Player Info and Last Played
    st.header(f"👤 You are: {st.session_state.player_name}")
    st.subheader(f"🎯 Turn: {game['players'][current_turn]['name']}")
    last_player_name = game["players"][last_player]["name"] if last_player else "None"
    st.subheader(f"🃕 Last Played: {', '.join(last_played) if last_played else 'Fresh Turn'} by {last_player_name}")

    # 🂠 Display Your Hand with Buttons    
    st.markdown("### Your Hand:")
    cols = st.columns(8)
    i = 0
    for card in hand:
        is_selected = card in st.session_state.selected_cards
        label = f"🟢 {card}" if is_selected else card
        if cols[i % 8].button(label, key=f"card_{i}"):
            if is_selected:
                st.session_state.selected_cards.remove(card)
            else:
                st.session_state.selected_cards.append(card)
        i += 1

    st.markdown(f"✅ Selected: {', '.join(st.session_state.selected_cards)}")
    
    # Its your Turn
    if current_turn == st.session_state.player_id:
        col1, col2 = st.columns(2)
        
       # If player click on Play
        with col1:
            if st.button("✅ Play"):
                ranks = [c[:-1] for c in st.session_state.selected_cards]
                if len(set(ranks)) == 1:
                    if not last_played or (len(st.session_state.selected_cards) == same_count and RANK_ORDER.index(ranks[0]) >= RANK_ORDER.index(last_played[0][:-1])):
                        new_hand = [c for c in hand if c not in st.session_state.selected_cards]
                        update_player_hand(st.session_state.room_code, st.session_state.player_id, new_hand)
                        update_game_field(st.session_state.room_code, "last_played", st.session_state.selected_cards)
                        time.sleep(0.1)
                        update_game_field(st.session_state.room_code, "same_count", len(st.session_state.selected_cards))
                        time.sleep(0.1)
                        update_game_field(st.session_state.room_code, "last_player", st.session_state.player_id)

                        for pid in game["players"].keys():
                            mark_player_pass(st.session_state.room_code, pid, False)
                        if not new_hand:
                            update_game_field(st.session_state.room_code, "winner", st.session_state.player_name)
                        else:
                            idx = game["turn_order"].index(current_turn)
                            next_pid = game["turn_order"][(idx + 1) % len(game["turn_order"])]
                            update_game_field(st.session_state.room_code, "current_turn", next_pid)
                        st.session_state.selected_cards = []
                        st.rerun()
                    
                    else:
                        st.warning("❌ Play doesn't beat the previous.")
                    st.session_state.selected_cards = []
                else:
                    st.warning("❌ All selected cards must be of same rank.")
                    
         # Getting fresh turn if all players pass except the last one...
        all_passed = all(
                    pid == game["last_player"] or p.get("passed")
                    for pid, p in game["players"].items()
                    )
        if all_passed:
                    update_game_field(st.session_state.room_code, "last_played", [])
                    update_game_field(st.session_state.room_code, "same_count", 0)
                    for pid in game["players"].keys():
                        mark_player_pass(st.session_state.room_code, pid, False)
                    update_game_field(st.session_state.room_code, "current_turn", last_player)

        # If player click on Pass...
        start = time.time()
        auto_pass = False
        while auto_pass != True:
            time_passed = (time.time() - start)
            if time_passed > 30:
                auto_pass = True
        if auto_pass == True:
            mark_player_pass(st.session_state.room_code, st.session_state.player_id)      
            idx = game["turn_order"].index(current_turn)
            next_pid = game["turn_order"][(idx + 1) % len(game["turn_order"])]
            update_game_field(st.session_state.room_code, "current_turn", next_pid)
            st.session_state.selected_cards = []
            st.rerun()
        with col2:
            if st.button("❌ Pass"):
                mark_player_pass(st.session_state.room_code, st.session_state.player_id)      
                idx = game["turn_order"].index(current_turn)
                next_pid = game["turn_order"][(idx + 1) % len(game["turn_order"])]
                update_game_field(st.session_state.room_code, "current_turn", next_pid)
                st.session_state.selected_cards = []
                st.rerun()

    else:
        st.info("⏳ Wait for your turn...")
