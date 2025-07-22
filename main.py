from streamlit_autorefresh import st_autorefresh
from firebase_admin import credentials, db, initialize_app
import streamlit as st
import uuid
from firebase import (
    create_room, join_room, get_game, update_game_field,
    update_player_hand, mark_player_pass
)
from game_engine import Card, RANK_ORDER


st.set_page_config(page_title="Multiplayer Card Game", layout="wide")
st.title("🃏 Multiplayer Card Game")
st_autorefresh(interval=2000, key="refresh")

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
        import random
        from game_engine import SUITS
        players = list(game["players"].keys())
        deck = [f"{rank}{suit}" for rank in RANK_ORDER for suit in SUITS]
        random.shuffle(deck)
        hands = {pid: [] for pid in players}
        for i, card in enumerate(deck):
            hands[players[i % len(players)]].append(card)
        for pid, hand in hands.items():
            update_player_hand(st.session_state.room_code, pid, hand)
        update_game_field(st.session_state.room_code, "turn_order", players)
        update_game_field(st.session_state.room_code, "current_turn", players[0])
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
    player_data = game["players"][st.session_state.player_id]
    hand = sorted(player_data["hand"], key=lambda c: RANK_ORDER.index(c[:-1]))
    current_turn = game["current_turn"]
    last_played = game.get("last_played", [])
    same_count = game.get("same_count", 0)
    last_player = game.get("last_player", "")

    if game.get("winner"):
        st.balloons()
        st.success(f"🎉 {game['winner']} WINS!")
        st.stop()

    st.header(f"👤 You are: {st.session_state.player_name}")
    st.subheader(f"🎯 Turn: {game['players'][current_turn]['name']}")
    st.markdown(f"🃕 Last Played: {', '.join(last_played) if last_played else 'Fresh Turn'}")

    st.markdown("### Your Hand:")
    cols = st.columns(8)
    for idx, card in enumerate(hand):
        is_selected = card in st.session_state.selected_cards
        label = f"🟢 {card}" if is_selected else card
        if cols[idx % 8].button(label, key=f"card_{idx}"):
            if is_selected:
                st.session_state.selected_cards.remove(card)
            else:
                st.session_state.selected_cards.append(card)

    st.markdown(f"✅ Selected: {', '.join(st.session_state.selected_cards)}")

    if current_turn == st.session_state.player_id:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Play"):
                ranks = [c[:-1] for c in st.session_state.selected_cards]
                if len(set(ranks)) == 1:
                    if not last_played or (len(st.session_state.selected_cards) == same_count and RANK_ORDER.index(ranks[0]) >= RANK_ORDER.index(last_played[0][:-1])):
                        new_hand = [c for c in hand if c not in st.session_state.selected_cards]
                        update_player_hand(st.session_state.room_code, st.session_state.player_id, new_hand)
                        update_game_field(st.session_state.room_code, "last_played", st.session_state.selected_cards)
                        update_game_field(st.session_state.room_code, "same_count", len(st.session_state.selected_cards))
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
                else:
                    st.warning("❌ All selected cards must be of same rank.")

        with col2:
            if st.button("❌ Pass"):
                mark_player_pass(st.session_state.room_code, st.session_state.player_id)
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
                else:
                    idx = game["turn_order"].index(current_turn)
                    next_pid = game["turn_order"][(idx + 1) % len(game["turn_order"])]
                    update_game_field(st.session_state.room_code, "current_turn", next_pid)
                st.session_state.selected_cards = []
                st.rerun()

    else:
        st.info("⏳ Wait for your turn...")
