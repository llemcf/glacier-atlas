import uuid
import re
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
from datetime import datetime

# --- IMPORT DES FONCTIONS MÉTIER ---
from utils import (
    load_csv_data, 
    get_rgi_glacier_names, 
    load_rgi_shapefile,
    fetch_image_from_nextcloud, 
    create_nextcloud_folder, 
    upload_to_nextcloud, slugify,
    optimize_image,
    CSV_PATH, 
    NEXTCLOUD_BASE,
    append_to_remote_csv,
)

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

# --- GESTION DE LA NAVIGATION (ROUTER) ---

if 'current_page' not in st.session_state:
    st.session_state.current_page = 'home'

def navigate_to(page_name):
    st.session_state.current_page = page_name
    st.rerun()

# ---------- Page d'accueil --------

def view_home():
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.title("❄️ Atlas des Glaciers")
    st.markdown("<h4 style='text-align: center; color: #7f8c8d; font-weight: 300;'>Mémoire visuelle et évolution des paysages glaciaires</h4>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("""Ce projet de rephotographie documente le recul des glaciers au cours du dernier siècle en superposant des archives historiques à des prises de vues contemporaines réalisées au même point de coordonnées.""")
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("Explorer l'Atlas"):
                navigate_to('atlas')
        with btn_col2:
            if st.button("Contribuer"):
                navigate_to('upload')

# ---------- Atlas des glaciers --------

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
            tooltip=f"{item['name']}",
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
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Fonction locale pour convertir l'image PIL en octets
                def get_image_bytes(img):
                    buf = io.BytesIO()
                    # Utilisation du format d'origine s'il est détecté, sinon JPEG par défaut
                    img_format = img.format if img.format else 'JPEG'
                    img.save(buf, format=img_format)
                    return buf.getvalue(), img_format.lower()
                
                bytes_old, ext_old = get_image_bytes(img_old)
                bytes_new, ext_new = get_image_bytes(img_new)
                
                # Affichage des boutons centrés sous le slider
                _, col_btn1, col_btn2, _ = st.columns([1, 2, 2, 1])
                
                with col_btn1:
                    st.download_button(
                        label=f"Télécharger l'archive ({selected_pair['old_date']})",
                        data=bytes_old,
                        file_name=f"{slugify(selected_pair['name'])}_{selected_pair['old_date']}.{ext_old}",
                        mime=f"image/{ext_old}",
                        use_container_width=True
                    )
                    
                with col_btn2:
                    st.download_button(
                        label=f"Télécharger la vue récente ({selected_pair['new_date']})",
                        data=bytes_new,
                        file_name=f"{slugify(selected_pair['name'])}_{selected_pair['new_date']}.{ext_new}",
                        mime=f"image/{ext_new}",
                        use_container_width=True
                    )
            else:
                st.error("Impossible de trouver ces images sur le serveur Nextcloud.")
                # Affichage des URL pour vous aider à débugger
                with st.expander("Détails techniques (pour le débug)"):
                    st.write("Vérifiez que ces liens renvoient bien vers un fichier image en cliquant dessus :")
                    st.markdown(f"- [Lien Archive ({selected_pair['old_img']})]({old_img_url})")
                    st.markdown(f"- [Lien Actuel ({selected_pair['new_img']})]({new_img_url})")
    else:
        st.info("Cliquez sur un point de la carte pour afficher l'évolution photographique en dessous.")

# ---------- Upload de nouvelles images --------

def view_upload():
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
    
    # ---------------------------------------------------------
    # ÉTAPE 1 : SAISIE DES DONNÉES (Sans st.form pour le temps réel)
    # ---------------------------------------------------------
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Informations générales")
        final_glacier_name = st.text_input("Nom du glacier", placeholder="Ex: Glacier du Tour")
        lat = st.number_input("Latitude du point de vue (ex: 45.9681)", format="%.5f", value=46.0000)
        lon = st.number_input("Longitude du point de vue (ex: 7.7951)", format="%.5f", value=7.0000)
        date_archive = st.number_input("Année de la photo d'archive", min_value=1850, max_value=int(datetime.now().year)-1, step=1, value=1930)
        date_rephoto = st.number_input("Année de votre photo (récente)", min_value=2000, max_value=int(datetime.now().year), step=1, value=2024)
        contributor = st.text_input("Nom du photographe ou de sa structure (Optionnel)")
        
    with col2:
        st.subheader("Fichiers photographiques")
        photo_archive = st.file_uploader("Importer la photo d'archive (Max 10 Mo)", type=['jpg', 'jpeg', 'png'])
        photo_rephoto = st.file_uploader("Importer la rephotographie (Max 10 Mo)", type=['jpg', 'jpeg', 'png'])
        
        st.subheader("Questionnaire Observateur")
        commentaires = st.text_area("Remarques additionnelles (météo, conditions d'accès...)")

    # ---------------------------------------------------------
    # ÉTAPE 2 : PRÉVISUALISATION ET VALIDATION TEMPS RÉEL
    # ---------------------------------------------------------
    if photo_archive and photo_rephoto:
        st.divider()
        st.subheader("Prévisualisation")
        
        # 1. Analyse du poids
        size_old_mb = photo_archive.size / (1024 * 1024)
        size_new_mb = photo_rephoto.size / (1024 * 1024)
        
        if size_old_mb > 80 or size_new_mb > 80:
            st.error(f"Vos images sont trop lourdes ({size_old_mb:.1f} Mo et {size_new_mb:.1f} Mo). La limite est de 80 Mo pour garantir la fluidité de l'affichage.")
            st.stop() # Bloque l'exécution du reste de la page
            
        # 2. Analyse de la géométrie (Proportions)
        img_old = Image.open(photo_archive)
        img_new = Image.open(photo_rephoto)
        
        ratio_old = img_old.width / img_old.height
        ratio_new = img_new.width / img_new.height
        
        # S'il y a plus de 5% de différence dans le ratio largeur/hauteur
        if abs(ratio_old - ratio_new) > 0.05:
            st.warning(f"**Attention au recadrage :** Vos deux images n'ont pas exactement les mêmes proportions. L'archive fait {img_old.width}x{img_old.height} et la nouvelle {img_new.width}x{img_new.height}. Le slider risque d'être décalé. Si possible, recadrez-les à l'identique sur votre ordinateur avant l'upload.")
            
        # 3. Génération du Slider de prévisualisation
        st.write("Vérifiez l'alignement de vos photos dans le comparateur ci-dessous avant d'envoyer :")
        _, col_preview, _ = st.columns([1, 4, 1])
        with col_preview:
            try:
                image_comparison(
                    img1=img_old,
                    img2=img_new,
                    label1=str(date_archive),
                    label2=str(date_rephoto),
                    width=700,
                    starting_position=50,
                    show_labels=True,
                    make_responsive=True
                )
            except Exception as e:
                st.error("Impossible de générer l'aperçu visuel.")

        # ---------------------------------------------------------
        # ÉTAPE 3 : ENVOI FINAL
        # ---------------------------------------------------------
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("Si le résultat visuel vous semble convenir, appuyez sur le bouton ci dessous.")
    
        if st.button("Envoyer ma contribution"):
            if not final_glacier_name:
                st.error("Veuillez remonter saisir un nom de glacier en haut du formulaire.")
            else:
                with st.spinner("Optimisation et envoi des photos sur le cloud..."):
                        pair_id = uuid.uuid4().hex[:4] 
                        slug_name = slugify(final_glacier_name)
                        
                        # Nous forçons l'extension à .webp puisque l'image sera convertie
                        name_old = f"{slug_name}_{pair_id}_{date_archive}_old.webp"
                        name_new = f"{slug_name}_{pair_id}_{date_rephoto}_new.webp"
                        
                        folder_path = slug_name
                        path_old = f"{folder_path}/{name_old}"
                        path_new = f"{folder_path}/{name_new}"
                        
                        # 1. Optimisation des images en mémoire
                        optimized_old_bytes = optimize_image(photo_archive)
                        optimized_new_bytes = optimize_image(photo_rephoto)
                        
                        # 2. Création du dossier et envoi
                        create_nextcloud_folder(folder_path)
                        up_old = upload_to_nextcloud(optimized_old_bytes, path_old)
                        up_new = upload_to_nextcloud(optimized_new_bytes, path_new)
                        
                        if up_old and up_new:
                            # Préparation de la ligne de données
                            new_data = {
                                "pair_id": f"{slug_name}_{pair_id}",
                                "glacier_name": final_glacier_name,
                                "lat": lat,
                                "lon": lon,
                                "year_old": date_archive,
                                "year_new": date_rephoto,
                                "img_old_path": path_old,
                                "img_new_path": path_new,
                                "contributor": contributor if contributor else "Anonyme"
                            }
                            
                            # Envoi direct vers le fichier CSV sur Nextcloud
                            if append_to_remote_csv(new_data):
                                st.success("Contribution envoyée avec succès. Les photos et les données sont enregistrées.")
                                load_csv_data.clear() # Force le rafraîchissement au prochain chargement de l'Atlas
                            else:
                                st.error("Erreur lors de la mise à jour de la base de données sur Nextcloud.")
                        else:
                            st.error("Erreur de communication avec le serveur Nextcloud lors de l'envoi des photos.")

# def view_upload():
#     col_retour, col_titre = st.columns([1, 5])
#     with col_retour:
#         st.markdown("<div class='btn-retour'>", unsafe_allow_html=True)
#         if st.button("← Retour Accueil"):
#             navigate_to('home')
#         st.markdown("</div>", unsafe_allow_html=True)
        
#     with col_titre:
#         st.markdown("<h2 style='margin-top: 0;'>Contribuer à l'Atlas</h2>", unsafe_allow_html=True)
#     st.divider()
    
#     st.write("Aidez-nous à documenter l'évolution des glaciers en partageant vos rephotographies.")
    
#     # Récupération des noms depuis le RGI
#     rgi_names = get_rgi_glacier_names()
    
#     with st.form("contribution_form"):
#         col1, col2 = st.columns(2)
        
#         with col1:
#             st.subheader("Informations générales")
            
#             # Champ de texte libre, tout simplement
#             final_glacier_name = st.text_input("Nom du glacier", placeholder="Ex: Glacier du Tour")
            
#             lat = st.number_input("Latitude du point de vue (ex: 45.9681)", format="%.5f", value=46.0000)
#             lon = st.number_input("Longitude du point de vue (ex: 7.7951)", format="%.5f", value=7.0000)
#             date_archive = st.number_input("Année de la photo d'archive", min_value=1850, max_value=int(datetime.now().year)-1, step=1, value=1930)
#             date_rephoto = st.number_input("Année de la photo récente", min_value=2000, max_value=int(datetime.now().year), step=1, value=2024)
#             contributor = st.text_input("Votre nom / structure (Optionnel)")
            
#         with col2:
#             st.subheader("Fichiers photographiques")
#             photo_archive = st.file_uploader("Importer la photo d'archive (ancienne)", type=['jpg', 'jpeg', 'png'])
#             photo_rephoto = st.file_uploader("Importer la rephotographie (récente)", type=['jpg', 'jpeg', 'png'])
            
#             st.subheader("Questionnaire Observateur")
#             commentaires = st.text_area("Remarques additionnelles (météo, conditions d'accès...)")
            
#         submit = st.form_submit_button("Envoyer ma contribution")
        
#         if submit:
#             if not final_glacier_name or final_glacier_name == "Sélectionnez...":
#                 st.error("Veuillez sélectionner ou saisir un nom de glacier.")
#             elif not photo_archive or not photo_rephoto:
#                 st.error("Veuillez uploader les deux photographies.")
#             else:
#                 with st.spinner("Création des dossiers et envoi des photos sur Nextcloud..."):
#                     pair_id = uuid.uuid4().hex[:4] # ID court unique
#                     slug_name = slugify(final_glacier_name)
                    
#                     # Construction des noms de fichiers propres
#                     ext_old = photo_archive.name.split('.')[-1].lower()
#                     ext_new = photo_rephoto.name.split('.')[-1].lower()
                    
#                     name_old = f"{slug_name}_{pair_id}_{date_archive}_old.{ext_old}"
#                     name_new = f"{slug_name}_{pair_id}_{date_rephoto}_new.{ext_new}"
                    
#                     folder_path = slug_name
#                     path_old = f"{folder_path}/{name_old}"
#                     path_new = f"{folder_path}/{name_new}"
                    
#                     # 1. Création du dossier du glacier
#                     create_nextcloud_folder(folder_path)
                    
#                     # 2. Upload des images
#                     up_old = upload_to_nextcloud(photo_archive.getvalue(), path_old)
#                     up_new = upload_to_nextcloud(photo_rephoto.getvalue(), path_new)
                    
#                     if up_old and up_new:
#                         # 3. Mise à jour du fichier CSV en local
#                         new_row = pd.DataFrame([{
#                             "pair_id": f"{slug_name}_{pair_id}",
#                             "glacier_name": final_glacier_name,
#                             "lat": lat,
#                             "lon": lon,
#                             "year_old": date_archive,
#                             "year_new": date_rephoto,
#                             "img_old_path": path_old,
#                             "img_new_path": path_new,
#                             "contributor": contributor if contributor else "Anonyme"
#                         }])
                        
#                         # Ajout à la suite du fichier existant
#                         new_row.to_csv(CSV_PATH, mode='a', header=False, index=False)
                        
#                         st.success("🎉 Contribution envoyée avec succès ! Les photos sont sur Nextcloud et la carte est mise à jour.")
#                         st.balloons()
                        
#                         # On vide le cache pour que la carte prenne en compte le nouveau point immédiatement
#                         load_csv_data.clear()
#                     else:
#                         st.error("Une erreur est survenue lors de l'envoi vers Nextcloud.")


# ==========================================
# AFFICHAGE DE LA PAGE COURANTE
# ==========================================
if st.session_state.current_page == 'home':
    view_home()
elif st.session_state.current_page == 'atlas':
    view_atlas()
elif st.session_state.current_page == 'upload':
    view_upload()