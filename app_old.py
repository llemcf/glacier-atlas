import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_image_comparison import image_comparison
from folium.plugins import MarkerCluster
from pathlib import Path
from PIL import Image

# --- CONFIGURATION DU SITE ---
st.set_page_config(
    layout="wide", 
    page_title="Atlas des Glaciers",
    page_icon="❄️" # Seul emoji autorisé (dans l'onglet du navigateur)
)

# --- CHARGEMENT CSS (DESIGN) ---
# C'est ici qu'on change le look de Streamlit pour le rendre "pro"
st.markdown("""
<style>
    /* Import d'une police élégante (Lato) */
    @import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Lato', sans-serif;
        color: #2c3e50;
    }
    
    /* Titres */
    h1 {
        font-weight: 300 !important;
        font-size: 2.5rem !important;
        color: #1a1a1a;
        margin-bottom: 0rem;
    }
    h2, h3 {
        font-weight: 400 !important;
        color: #4a4a4a;
    }
    
    /* Retirer la barre colorée en haut de Streamlit */
    header {visibility: hidden;}
    
    /* Espacement global */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Style des boites d'info */
    .stAlert {
        background-color: #f8f9fa;
        border: none;
        color: #666;
    }
</style>
""", unsafe_allow_html=True)

# --- CHEMINS ---
DATA_DIR = Path("data")
IMAGES_DIR = DATA_DIR / "images"
CSV_PATH = DATA_DIR / "glacier_inventory.csv"

# --- FONCTIONS (LOGIQUE) ---
@st.cache_data
def load_and_process_data():
    if not CSV_PATH.exists():
        return []
    df = pd.read_csv(CSV_PATH)
    pairs = []
    df['id'] = df.index
    processed_ids = set()

    # Stratégie 1 : Exact
    strict_groups = df.groupby(['name', 'lat_photo', 'lon_photo'])
    for (name, lat, lon), group in strict_groups:
        old = group[group['state'] == 'old']
        new = group[group['state'] == 'new']
        if not old.empty and not new.empty:
            pairs.append({
                "id": f"{name}_{old.iloc[0]['id']}",
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

    # Stratégie 2 : Approximatif
    leftovers = df[~df['id'].isin(processed_ids)]
    for name, group in leftovers.groupby('name'):
        old = group[group['state'] == 'old']
        new = group[group['state'] == 'new']
        if len(old) == 1 and len(new) == 1:
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

def load_image(filename):
    path = IMAGES_DIR / filename
    if path.exists():
        return Image.open(path)
    return None

# --- UI PRINCIPALE ---
pairs_data = load_and_process_data()

# En-tête minimaliste
st.title("Atlas Historique des Glaciers")
st.markdown("Une documentation visuelle de l'évolution glaciaire dans les Alpes (1920 - 2024).")
st.divider() # Une ligne fine et propre

if not pairs_data:
    st.error("Données non trouvées.")
    st.stop()

col_map, col_padding, col_details = st.columns([1.2, 0.1, 1])

# --- COLONNE GAUCHE : CARTE ÉPURÉE ---
with col_map:
    # Calcul du centre
    start_lat = sum(p['lat'] for p in pairs_data) / len(pairs_data)
    start_lon = sum(p['lon'] for p in pairs_data) / len(pairs_data)
    
    # Fond de carte "Positron" (Gris clair, minimaliste, fait ressortir les points)
    m = folium.Map(
        location=[start_lat, start_lon], 
        zoom_start=9,
        #tiles="Cartodb Positron"
    )
    
    # Clusters personnalisés (optionnel, sinon retirer MarkerCluster)
    marker_cluster = MarkerCluster().add_to(m)

    for item in pairs_data:
        # On utilise CircleMarker : des points ronds, nets, sans l'icône "Google Maps"
        folium.CircleMarker(
            location=[item['lat'], item['lon']],
            radius=8,
            popup=item['id'],
            tooltip=item['name'],
            color="#2E86C1",      # Un bleu glacier profond
            fill=True,
            fill_color="#2E86C1",
            fill_opacity=0.7,
            weight=1
        ).add_to(marker_cluster)

    map_output = st_folium(m, width="100%", height=650)

# --- COLONNE DROITE : DÉTAILS ---
with col_details:
    selected_pair = None
    if map_output['last_object_clicked_popup']:
        clicked_id = map_output['last_object_clicked_popup']
        selected_pair = next((p for p in pairs_data if p['id'] == clicked_id), None)
    
    if selected_pair:
        # Titre propre
        st.markdown(f"### {selected_pair['name']}")
        
        # Métadonnées en gris clair, petites
        st.markdown(
            f"""
            <div style='color: #666; font-size: 0.9em; margin-bottom: 20px;'>
            Point de vue : {selected_pair['lat']:.4f}, {selected_pair['lon']:.4f} <br>
            Intervalle : {selected_pair['new_date'] - selected_pair['old_date']} ans
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        img_old = load_image(selected_pair['old_img'])
        img_new = load_image(selected_pair['new_img'])
        
        if img_old and img_new:
            # Le slider
            image_comparison(
                img1=img_old,
                img2=img_new,
                label1=f"Archive {selected_pair['old_date']}",
                label2=f"Actuel {selected_pair['new_date']}",
                width=700,
                starting_position=50,
                show_labels=True,
                make_responsive=True,
                in_memory=True
            )
            
            # Petit texte explicatif ou téléchargement (optionnel)
            st.caption("Déplacez le curseur central pour comparer les époques.")
            
        else:
            st.warning("Images non disponibles pour ce point.")
            
    else:
        # Message d'accueil "Vide" élégant
        st.markdown("""
            <div style='text-align: center; color: #aaa; margin-top: 150px;'>
                <h3>Sélectionnez un glacier</h3>
                <p>Cliquez sur un point bleu sur la carte pour révéler un avant/après du glacier.</p>
            </div>
        """, unsafe_allow_html=True)