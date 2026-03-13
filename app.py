import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from streamlit_image_comparison import image_comparison
import geopandas as gpd
from shapely.geometry import box
import urllib.parse
from pathlib import Path
from requests.auth import HTTPBasicAuth
import requests
import io
from PIL import Image

# ==========================================
# CONFIGURATION ET DESIGN CSS
# ==========================================
st.set_page_config(page_title="Atlas des Glaciers", layout="wide", initial_sidebar_state="collapsed")

# Injection de CSS pour l'esthétique "Bleu Glace" et minimaliste
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@200;300;400;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Montserrat', sans-serif;
    }
    
    /* Titres élégants */
    h1 {
        font-weight: 200 !important;
        color: #005c8a !important;
        text-align: center;
        letter-spacing: 2px;
    }
    h2, h3 {
        font-weight: 300 !important;
        color: #0083B0 !important;
    }

    /* Boutons personnalisés "Bleu Glace" */
    .stButton > button {
        background: linear-gradient(135deg, #0083B0 0%, #00B4DB 100%);
        color: white;
        border: none;
        border-radius: 30px;
        padding: 10px 25px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0, 131, 176, 0.3);
        color: white;
    }
    
    /* Bouton retour plus discret */
    .btn-retour > .stButton > button {
        background: #e0f7fa;
        color: #0083B0;
        border: 1px solid #0083B0;
        width: auto;
    }
    .btn-retour > .stButton > button:hover {
        background: #b2ebf2;
    }
    
    /* Masquer les éléments inutiles de Streamlit */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# GESTION DE LA NAVIGATION (ROUTER)
# ==========================================
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'

def navigate_to(page_name):
    st.session_state.current_page = page_name
    st.rerun()

# ==========================================
# FONCTIONS DONNÉES ET CARTOGRAPHIE
# ==========================================
CSV_PATH = Path("data/glacier_inventory.csv")
RGI_PATH = Path("data/randolph_glacier_inventory_7/rgi2000_v70_vector.shp")
NEXTCLOUD_BASE = "https://nextcloud.mountainwilderness.fr/public.php/webdav/glacier_atlas/images/"

@st.cache_data
def load_csv_data():
    if not CSV_PATH.exists():
        return []
    df = pd.read_csv(CSV_PATH)
    pairs = []
    df['id'] = df.index
    
    for name, group in df.groupby('name'):
        old = group[group['state'] == 'old']
        new = group[group['state'] == 'new']
        if not old.empty and not new.empty:
            pairs.append({
                "id": f"{name}_{old.iloc[0]['id']}",
                "name": name,
                "lat": new.iloc[0]['lat_photo'],
                "lon": new.iloc[0]['lon_photo'],
                "old_img": old.iloc[0]['filename'],
                "new_img": new.iloc[0]['filename'],
                "old_date": old.iloc[0]['date'],
                "new_date": new.iloc[0]['date']
            })
    return pairs

@st.cache_data
def load_rgi_shapefile(bounds):
    """
    Charge le shapefile RGI de manière intelligente.
    Au lieu de charger la planète entière (ce qui ferait planter le serveur),
    on ne charge que la zone géographique de vos photos (bbox=bounds).
    """
    if not RGI_PATH.exists():
        return None
    try:
        # bounds = (min_lon, min_lat, max_lon, max_lat)
        return gpd.read_file(RGI_PATH, bbox=bounds)
    except Exception as e:
        st.error(f"Erreur lors du chargement RGI : {e}")
        return None
    
@st.cache_data(show_spinner=False)
def fetch_image_from_nextcloud(url):
    """Télécharge l'image via l'API WebDAV officielle de Nextcloud."""
    try:
        # Le nom d'utilisateur est le token secret du partage
        auth = HTTPBasicAuth('dGjHCTLdJx6xmPq', '')
        
        # On rassure la sécurité de Nextcloud
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        
        response = requests.get(url, auth=auth, headers=headers, timeout=15)
        
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        else:
            print(f"Erreur Nextcloud : {response.status_code} sur {url}")
            return None
    except Exception as e:
        print(f"Exception : {e}")
        return None

# ==========================================
# VUES (PAGES)
# ==========================================

def view_home():
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.title("❄️ Atlas des Glaciers")
    st.markdown("<h4 style='text-align: center; color: #7f8c8d; font-weight: 300;'>Mémoire visuelle et évolution des paysages glaciaires</h4>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("""
        *Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.*
        
        Ce projet de rephotographie documente le recul des glaciers au cours du dernier siècle en superposant des archives historiques à des prises de vues contemporaines réalisées au même point de coordonnées.
        """)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("🗺️ Explorer l'Atlas"):
                navigate_to('atlas')
        with btn_col2:
            if st.button("📸 Contribuer & Uploader"):
                navigate_to('upload')

def view_atlas():
    # En-tête avec bouton retour
    col_retour, col_titre = st.columns([1, 5])
    with col_retour:
        st.markdown("<div class='btn-retour'>", unsafe_allow_html=True)
        if st.button("← Retour Accueil"):
            navigate_to('home')
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_titre:
        st.markdown("<h2 style='margin-top: 0;'>Cartographie Interactive</h2>", unsafe_allow_html=True)
    
    st.divider()

    pairs_data = load_csv_data()
    if not pairs_data:
        st.warning("Aucune donnée disponible. Vérifiez glacier_inventory.csv.")
        return

    # 1. Calcul de l'étendue spatiale (Bounding Box) pour le filtre RGI
    lats = [p['lat'] for p in pairs_data]
    lons = [p['lon'] for p in pairs_data]
    center_lat, center_lon = sum(lats)/len(lats), sum(lons)/len(lons)
    
    # On crée une "boîte" autour des points (avec une marge de 0.2 degrés)
    min_lon, min_lat = min(lons) - 0.2, min(lats) - 0.2
    max_lon, max_lat = max(lons) + 0.2, max(lats) + 0.2
    bbox = (min_lon, min_lat, max_lon, max_lat)

    # 2. LA CARTE ÉPURÉE
    m = folium.Map(location=[center_lat, center_lon], zoom_start=9, tiles="CartoDB positron")

    # 3. Ajout du Shapefile RGI (Formes Glaciaires)
    rgi_gdf = load_rgi_shapefile(bbox)
    if rgi_gdf is not None and not rgi_gdf.empty:
        folium.GeoJson(
            rgi_gdf,
            style_function=lambda x: {
                'fillColor': '#B2EBF2', # Bleu très clair
                'color': '#0083B0',     # Bordure bleu glace
                'weight': 1,
                'fillOpacity': 0.6
            },
            name="Glaciers RGI"
        ).add_to(m)

    # 4. Ajout des Marqueurs Photos
    for item in pairs_data:
        folium.CircleMarker(
            location=[item['lat'], item['lon']],
            radius=7,
            popup=item['id'], # ID caché pour récupérer le clic
            tooltip=f"{item['name']} 📸",
            color="#FFFFFF",
            fill=True,
            fill_color="#005c8a",
            fill_opacity=0.9,
            weight=2
        ).add_to(m)

    # Affichage de la carte
    map_output = st_folium(m, width="100%", height=500, returned_objects=["last_object_clicked_popup"])

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. AFFICHAGE DU SLIDER EN DESSOUS DE LA CARTE
    if map_output and map_output.get('last_object_clicked_popup'):
        clicked_id = map_output['last_object_clicked_popup']
        selected_pair = next((p for p in pairs_data if p['id'] == clicked_id), None)
        
        if selected_pair:
            st.markdown(f"<h3 style='text-align: center;'>{selected_pair['name']}</h3>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: #7f8c8d;'>Comparaison {selected_pair['old_date']} - {selected_pair['new_date']}</p>", unsafe_allow_html=True)
            
            old_img_url = NEXTCLOUD_BASE + urllib.parse.quote(selected_pair['old_img'])
            new_img_url = NEXTCLOUD_BASE + urllib.parse.quote(selected_pair['new_img'])
            
            # 3. Le téléchargement via la fonction sécurisée que nous avons créée à l'étape précédente
            with st.spinner("Téléchargement des images depuis Nextcloud..."):
                img_old = fetch_image_from_nextcloud(old_img_url)
                img_new = fetch_image_from_nextcloud(new_img_url)
            
            # On vérifie que les DEUX images ont bien été trouvées
            if img_old is not None and img_new is not None:
                _, col_slider, _ = st.columns([1, 4, 1])
                with col_slider:
                    image_comparison(
                        img1=img_old, # On passe l'image chargée, plus l'URL
                        img2=img_new,
                        label1=str(selected_pair['old_date']),
                        label2=str(selected_pair['new_date']),
                        width=800,
                        starting_position=50,
                        show_labels=True,
                        make_responsive=True
                    )
            else:
                st.error("⚠️ Impossible de trouver ces images sur le serveur Nextcloud.")
                # Affichage des URL pour vous aider à débugger
                with st.expander("Détails techniques (pour le débug)"):
                    st.write("Vérifiez que ces liens renvoient bien vers un fichier image en cliquant dessus :")
                    st.markdown(f"- [Lien Archive ({selected_pair['old_img']})]({old_img_url})")
                    st.markdown(f"- [Lien Actuel ({selected_pair['new_img']})]({new_img_url})")
    else:
        st.info("👆 Cliquez sur un point de la carte pour afficher l'évolution photographique en dessous.")

def view_upload():
    # En-tête
    col_retour, col_titre = st.columns([1, 5])
    with col_retour:
        st.markdown("<div class='btn-retour'>", unsafe_allow_html=True)
        if st.button("← Retour Accueil"):
            navigate_to('home')
        st.markdown("</div>", unsafe_allow_html=True)
        
    with col_titre:
        st.markdown("<h2 style='margin-top: 0;'>Contribuer à l'Atlas</h2>", unsafe_allow_html=True)
    st.divider()
    
    st.write("Aidez-nous à documenter l'évolution des glaciers en partageant vos rephotographies.")
    
    with st.form("contribution_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Informations générales")
            glacier_name = st.text_input("Nom du glacier")
            lat = st.number_input("Latitude (ex: 45.9681)", format="%.5f")
            lon = st.number_input("Longitude (ex: 7.7951)", format="%.5f")
            date_archive = st.number_input("Année de la photo d'archive", min_value=1800, max_value=2024, step=1)
            date_rephoto = st.number_input("Année de votre photo", min_value=1800, max_value=2024, step=1)
            
        with col2:
            st.subheader("Fichiers photographiques")
            photo_archive = st.file_uploader("Importer la photo d'archive (Ancienne)", type=['jpg', 'png'])
            photo_rephoto = st.file_uploader("Importer la rephotographie (Récemment)", type=['jpg', 'png'])
            
            st.subheader("Questionnaire Observateur")
            evolution_percue = st.select_slider(
                "Comment évaluez-vous le retrait glaciaire sur ce point ?",
                options=["Faible", "Modéré", "Important", "Spectaculaire"]
            )
            commentaires = st.text_area("Remarques additionnelles (météo, conditions d'accès...)")
            
        submit = st.form_submit_button("Envoyer ma contribution")
        
        if submit:
            st.success("Merci ! Vos données ont été enregistrées (Simulation).")

# ==========================================
# AFFICHAGE DE LA PAGE COURANTE
# ==========================================
if st.session_state.current_page == 'home':
    view_home()
elif st.session_state.current_page == 'atlas':
    view_atlas()
elif st.session_state.current_page == 'upload':
    view_upload()