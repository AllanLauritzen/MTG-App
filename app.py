import streamlit as st
from supabase import create_client, Client
import urllib.request
import json
import datetime

# Supabase setup
SUPABASE_URL = "https://mjvgcagaxzeyappdciti.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1qdmdjYWdheHpleWFwcGRjaXRpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjU4Nzk0NzcsImV4cCI6MjA4MTQ1NTQ3N30.MkSvy359kPwNwvZQ5aynZCWCpJpxoMUgHr7ruRxg7hI"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Deck Styrke App - Commander Tracking")

# Funktion til at fetch commander image fra Scryfall
def fetch_commander_image(commander_name):
    try:
        url = f"https://api.scryfall.com/cards/named?fuzzy={urllib.parse.quote(commander_name)}"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read())
            if 'image_uris' in data and 'png' in data['image_uris']:
                return data['image_uris']['png']
            else:
                return "https://via.placeholder.com/150"  # Default hvis ikke fundet
    except:
        return "https://via.placeholder.com/150"  # Fejlhåndtering

# Sektion: Spillere
st.header("Spillere")
def get_players():
    return supabase.table("players").select("*").execute().data

players = get_players()
for p in players:
    st.write(f"{p['name']} ({p['email']})")
    if p['image_url']:
        st.image(p['image_url'], width=100)

with st.form("Tilføj spiller"):
    name = st.text_input("Navn")
    email = st.text_input("Email")
    image_file = st.file_uploader("Upload billede")
    submit = st.form_submit_button("Tilføj")
    if submit:
        image_url = ""
        if image_file:
            image_path = f"images/{image_file.name}"
            supabase.storage.from_("images").upload(image_path, image_file.getvalue())
            image_url = supabase.storage.from_("images").get_public_url(image_path)['public_url']
        data = {"name": name, "email": email, "image_url": image_url}
        supabase.table("players").insert(data).execute()
        st.success("Spiller tilføjet!")

# Sektion: Decks
st.header("Commander Decks")
def get_decks():
    return supabase.table("decks").select("*").execute().data

decks = get_decks()
player_dict = {p['id']: p['name'] for p in players}
for d in decks:
    st.write(f"{d['commander_name']} (af {player_dict.get(d['player_id'], 'Ukendt')})")
    if d['commander_image_url']:
        st.image(d['commander_image_url'], width=200)

with st.form("Tilføj deck"):
    player_id = st.selectbox("Vælg spiller", options=[(p['id'], p['name']) for p in players], format_func=lambda x: x[1])
    commander_name = st.text_input("Commander navn")
    submit = st.form_submit_button("Tilføj")
    if submit:
        image_url = fetch_commander_image(commander_name)
        data = {"player_id": player_id[0], "commander_name": commander_name, "commander_image_url": image_url}
        supabase.table("decks").insert(data).execute()
        st.success("Deck tilføjet med auto-fetch billede!")

# Sektion: Matches og placements
st.header("Tilføj match-resultat")
deck_dict = {d['id']: d['commander_name'] for d in decks}
with st.form("Ny match"):
    selected_decks = st.multiselect("Vælg 4 decks i pod'en", options=list(deck_dict.keys()), format_func=lambda x: deck_dict[x], max_selections=4)
    placements = {}
    for deck_id in selected_decks:
        placements[deck_id] = st.number_input(f"Placement for {deck_dict[deck_id]} (1-4)", min_value=1, max_value=4)
    submit = st.form_submit_button("Gem match")
    if submit and len(selected_decks) == 4:
        match_data = {"match_date": datetime.datetime.now().isoformat()}
        match_insert = supabase.table("matches").insert(match_data).execute()
        match_id = match_insert.data[0]['id']
        for deck_id, placement in placements.items():
            supabase.table("placements").insert({"match_id": match_id, "deck_id": deck_id, "placement": placement}).execute()
        st.success("Match gemt!")

# Sektion: Styrke-forhold
st.header("Styrke Ranking")
placements_data = supabase.table("placements").select("*").execute().data
if placements_data:
    # Simpel beregning: Gennemsnit placement per deck (lavere = bedre)
    deck_stats = {}
    for p in placements_data:
        deck_id = p['deck_id']
        if deck_id not in deck_stats:
            deck_stats[deck_id] = {'placements': [], 'name': deck_dict.get(deck_id, 'Ukendt')}
        deck_stats[deck_id]['placements'].append(p['placement'])
    
    ranking = []
    for deck_id, stats in deck_stats.items():
        avg_placement = sum(stats['placements']) / len(stats['placements'])
        ranking.append((stats['name'], avg_placement, len(stats['placements'])))
    
    ranking.sort(key=lambda x: x[1])  # Sorter efter laveste gennemsnit
    st.table([{"Deck": name, "Gennemsnit Placement": f"{avg:.2f}", "Antal Matches": count} for name, avg, count in ranking])
else:
    st.write("Ingen matches endnu – tilføj nogle for at se ranking!")
