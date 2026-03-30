import streamlit as st
import pandas as pd
import geopandas as gpd
import requests
from requests.auth import HTTPBasicAuth
import io
from PIL import Image
import re
from pathlib import Path

# --- CONSTANTES ---
CSV_PATH = Path("data/glacier_inventory.csv")
RGI_PATH = Path("data/randolph_glacier_inventory_7/rgi2000_v70_vector.shp")
NEXTCLOUD_BASE = "https://nextcloud.mountainwilderness.fr/public.php/webdav/glacier_atlas/images/"
CSV_REMOTE_URL = "https://nextcloud.mountainwilderness.fr/public.php/webdav/glacier_atlas/glacier_inventory.csv"

# --- UTILITAIRES ---
def slugify(text):
    """Transforme 'Mer de Glace' en 'mer-de-glace'"""
    return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')

# --- LECTURE DES DONNÉES ---
# @st.cache_data
# def load_csv_data():
#     """Charge l'inventaire des glaciers."""
#     if not CSV_PATH.exists():
#         return []
#     df = pd.read_csv(CSV_PATH)
#     pairs = []
#     for _, row in df.iterrows():
#         pairs.append({
#             "id": row['pair_id'],
#             "name": row['glacier_name'],
#             "lat": row['lat'],
#             "lon": row['lon'],
#             "old_img": row['img_old_path'],
#             "new_img": row['img_new_path'],
#             "old_date": row['year_old'],
#             "new_date": row['year_new']
#         })
#     return pairs

@st.cache_data(ttl=60) # Le cache expire toutes les minutes pour voir les nouveautés
def load_csv_data():
    """Charge l'inventaire des glaciers directement depuis Nextcloud."""
    auth = HTTPBasicAuth('dGjHCTLdJx6xmPq', '')
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    
    try:
        response = requests.get(CSV_REMOTE_URL, auth=auth, headers=headers, timeout=10)
        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            pairs = []
            for _, row in df.iterrows():
                pairs.append({
                    "id": row['pair_id'],
                    "name": row['glacier_name'],
                    "lat": row['lat'],
                    "lon": row['lon'],
                    "old_img": row['img_old_path'],
                    "new_img": row['img_new_path'],
                    "old_date": row['year_old'],
                    "new_date": row['year_new']
                })
            return pairs
        return []
    except Exception as e:
        print(f"Erreur de lecture du CSV distant : {e}")
        return []

@st.cache_data
def get_rgi_glacier_names():
    """Extrait la liste des noms de glaciers depuis le shapefile RGI."""
    try:
        gdf = gpd.read_file(RGI_PATH)
        name_col = 'glac_name' if 'glac_name' in gdf.columns else 'Name'
        if name_col in gdf.columns:
            names = gdf[name_col].dropna().unique().tolist()
            return sorted([n for n in names if n.strip() != ""])
        return []
    except Exception:
        return []

@st.cache_data
def load_rgi_shapefile(bounds):
    """Charge la portion du shapefile RGI correspondant à la vue."""
    if not RGI_PATH.exists():
        return None
    try:
        return gpd.read_file(RGI_PATH, bbox=bounds)
    except Exception as e:
        st.error(f"Erreur lors du chargement RGI : {e}")
        return None

# --- INTERACTIONS NEXTCLOUD ---
@st.cache_data(show_spinner=False)
def fetch_image_from_nextcloud(url):
    """Télécharge l'image via l'API WebDAV officielle de Nextcloud."""
    try:
        auth = HTTPBasicAuth('dGjHCTLdJx6xmPq', '')
        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        }
        response = requests.get(url, auth=auth, headers=headers, timeout=15)
        if response.status_code == 200:
            return Image.open(io.BytesIO(response.content))
        else:
            return None
    except Exception:
        return None

def create_nextcloud_folder(folder_name):
    """Crée un dossier sur Nextcloud via WebDAV (Méthode MKCOL)."""
    url = f"{NEXTCLOUD_BASE}{folder_name}"
    auth = HTTPBasicAuth('dGjHCTLdJx6xmPq', '')
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    response = requests.request('MKCOL', url, auth=auth, headers=headers)
    return response.status_code in [201, 405]

def upload_to_nextcloud(file_bytes, remote_path):
    """Uploade un fichier sur Nextcloud via WebDAV (Méthode PUT)."""
    url = f"{NEXTCLOUD_BASE}{remote_path}"
    auth = HTTPBasicAuth('dGjHCTLdJx6xmPq', '')
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    response = requests.put(url, data=file_bytes, auth=auth, headers=headers)
    return response.status_code in [201, 204]

def append_to_remote_csv(new_row_dict):
    """Télécharge le CSV, ajoute la nouvelle ligne, et l'écrase sur Nextcloud."""
    auth = HTTPBasicAuth('dGjHCTLdJx6xmPq', '')
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    
    # 1. Télécharger le CSV actuel
    response = requests.get(CSV_REMOTE_URL, auth=auth, headers=headers)
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
    else:
        # Fichier introuvable, création d'un DataFrame vide avec les bonnes colonnes
        df = pd.DataFrame(columns=[
            "pair_id", "glacier_name", "lat", "lon", "year_old", 
            "year_new", "img_old_path", "img_new_path", "contributor"
        ])
        
    # 2. Ajouter la nouvelle ligne
    new_row_df = pd.DataFrame([new_row_dict])
    df = pd.concat([df, new_row_df], ignore_index=True)
    
    # 3. Convertir en texte et uploader
    csv_content = df.to_csv(index=False).encode('utf-8')
    put_response = requests.put(CSV_REMOTE_URL, data=csv_content, auth=auth, headers=headers)
    
    return put_response.status_code in [201, 204]

# --- OPTIMISATION DES IMAGES ---

def optimize_image(file_buffer, max_width=2000, quality=80):
    """
    Optimise une image uploadée : redimensionnement proportionnel,
    conversion en RGB et compression au format WebP.
    """
    img = Image.open(file_buffer)
    
    # Conversion en RGB si l'image comporte un canal alpha (transparence d'un PNG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        
    # Redimensionnement si l'image dépasse la largeur maximale autorisée
    if img.width > max_width:
        ratio = max_width / float(img.width)
        new_height = int((float(img.height) * float(ratio)))
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
    # Sauvegarde de l'image optimisée dans un nouveau buffer mémoire en format WebP
    output_buffer = io.BytesIO()
    img.save(output_buffer, format="WEBP", quality=quality, method=6)
    
    return output_buffer.getvalue()