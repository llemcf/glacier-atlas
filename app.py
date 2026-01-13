import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_image_comparison import image_comparison
from folium.plugins import MarkerCluster
from pathlib import Path
from PIL import Image

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Atlas des Glaciers")
DATA_DIR = Path("data")
IMAGES_DIR = DATA_DIR / "images"
CSV_PATH = DATA_DIR / "glacier_inventory.csv"

# --- FONCTION DE CHARGEMENT DES DONNÉES ---
@st.cache_data
def load_and_process_data():
    """
    Charge le CSV et associe intelligemment les photos 'old' et 'new'.
    Gère les légers décalages GPS et les points de vue multiples.
    """
    if not CSV_PATH.exists():
        return []

    df = pd.read_csv(CSV_PATH)
    pairs = []
    
    # 1. On identifie les paires par nom + coord exactes (cas idéal)
    # On crée un ID unique pour chaque ligne pour suivre celles qu'on a traitées
    df['id'] = df.index
    processed_ids = set()

    # Stratégie 1 : Groupement strict (Même nom, même position GPS)
    strict_groups = df.groupby(['name', 'lat_photo', 'lon_photo'])
    
    for (name, lat, lon), group in strict_groups:
        old = group[group['state'] == 'old']
        new = group[group['state'] == 'new']
        
        if not old.empty and not new.empty:
            # On a trouvé une paire parfaite
            pairs.append({
                "id": f"{name}_{old.iloc[0]['id']}", # ID unique pour le système
                "name": name,
                "lat": lat,
                "lon": lon,
                "old_img": old.iloc[0]['filename'],
                "new_img": new.iloc[0]['filename'],
                "old_date": old.iloc[0]['date'],
                "new_date": new.iloc[0]['date']
            })
            processed_ids.update(old['id'])
            processed_ids.update(new['id'])

    # Stratégie 2 : Récupération des orphelins (ex: Morteratsch avec GPS légèrement différent)
    # On regarde les lignes non traitées
    leftovers = df[~df['id'].isin(processed_ids)]
    
    # On essaye de les grouper juste par nom
    for name, group in leftovers.groupby('name'):
        old = group[group['state'] == 'old']
        new = group[group['state'] == 'new']
        
        # S'il reste exactement 1 vieux et 1 neuf pour ce nom, on les marie
        if len(old) == 1 and len(new) == 1:
            # On utilise la position du 'new' (supposée plus précise)
            pairs.append({
                "id": f"{name}_fuzzy_{old.iloc[0]['id']}",
                "name": name,
                "lat": new.iloc[0]['lat_photo'],
                "lon": new.iloc[0]['lon_photo'],
                "old_img": old.iloc[0]['filename'],
                "new_img": new.iloc[0]['filename'],
                "old_date": old.iloc[0]['date'],
                "new_date": new.iloc[0]['date']
            })
            
    return pairs

# --- FONCTION UTILITAIRE IMAGE ---
def load_image(filename):
    """Charge une image depuis le disque avec PIL"""
    path = IMAGES_DIR / filename
    if path.exists():
        return Image.open(path)
    else:
        return None

# --- INTERFACE PRINCIPALE ---
st.title("🧊 Atlas Interactif des Glaciers")
st.markdown("Documentation de l'évolution glaciaire par **rephotographie** (1920-2024).")

# Chargement des données
pairs_data = load_and_process_data()

if not pairs_data:
    st.error(f"⚠️ Impossible de charger les données. Vérifiez que le fichier existe : {CSV_PATH}")
    st.stop()

# Mise en page : Carte à gauche (ou haut), Détails à droite (ou bas)
col_map, col_details = st.columns([1, 1])

with col_map:
    st.subheader("Carte des observations")
    
    # Centrage de la carte (moyenne des points ou centrage fixe Alpes)
    start_lat = sum(p['lat'] for p in pairs_data) / len(pairs_data)
    start_lon = sum(p['lon'] for p in pairs_data) / len(pairs_data)
    
    m = folium.Map(location=[start_lat, start_lon], zoom_start=9)
    
    # Utilisation d'un Cluster pour gérer les points proches (ex: Gornergletscher)
    marker_cluster = MarkerCluster().add_to(m)

    # Ajout des marqueurs
    for item in pairs_data:
        folium.Marker(
            location=[item['lat'], item['lon']],
            tooltip=f"{item['name']} ({item['new_date']})",
            # On stocke l'ID unique dans le popup ou on l'utilise pour la logique de clic
            # Ici l'astuce : le tooltip sert de clé de sélection simplifiée, 
            # mais attention aux doublons de noms.
            # Pour être robuste, on va utiliser l'ID interne si possible, 
            # mais st_folium renvoie le tooltip ou le popup.
            popup=item['id'], 
            icon=folium.Icon(color="blue", icon="camera", prefix='fa')
        ).add_to(marker_cluster)

    # Affichage de la carte
    map_output = st_folium(m, width="100%", height=600)

with col_details:
    st.subheader("Analyse comparative")
    
    selected_pair = None
    
    # Logique de sélection via la carte
    if map_output['last_object_clicked_popup']:
        clicked_id = map_output['last_object_clicked_popup']
        # On retrouve la donnée associée à cet ID
        selected_pair = next((p for p in pairs_data if p['id'] == clicked_id), None)
    
    # Affichage
    if selected_pair:
        st.markdown(f"### 🏔️ {selected_pair['name']}")
        st.caption(f"Position : {selected_pair['lat']}, {selected_pair['lon']}")
        
        # Chargement des images
        img_old = load_image(selected_pair['old_img'])
        img_new = load_image(selected_pair['new_img'])
        
        if img_old and img_new:
            # Le composant de comparaison
            st.write(f"Comparaison **{selected_pair['old_date']}** vs **{selected_pair['new_date']}**")
            image_comparison(
                img1=img_old,
                img2=img_new,
                label1=str(selected_pair['old_date']),
                label2=str(selected_pair['new_date']),
                width=700,
                starting_position=50,
                show_labels=True,
                make_responsive=True,
                in_memory=True # Important pour PIL images
            )
        else:
            st.warning(f"⚠️ Une des images est introuvable dans `{IMAGES_DIR}`.")
            st.write(f"Fichiers attendus : `{selected_pair['old_img']}` et `{selected_pair['new_img']}`")
            
    else:
        st.info("👆 Cliquez sur un marqueur bleu (ou un groupe de marqueurs) sur la carte pour afficher la comparaison.")