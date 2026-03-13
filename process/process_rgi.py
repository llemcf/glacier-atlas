import geopandas as gpd
from pathlib import Path
import os

# --- Chemins d'accès ---
INPUT_FILE = Path("data/randolph_glacier_inventory_7_init/rgi2000_v70_vector.shp")
OUTPUT_DIR = Path("data/randolph_glacier_inventory_7")
OUTPUT_FILE = OUTPUT_DIR / "rgi2000_v70_vector.shp"

# Surface minimum en km² (0.1 km² = 10 hectares)
MIN_AREA_KM2 = 0.1 

# Bounding box des Alpes (min_lon, min_lat, max_lon, max_lat)
ALPS_BBOX = (5.0, 43.0, 16.5, 48.5)

def process_rgi():
    print("🏔️ Début du traitement du fichier RGI...")
    
    if not INPUT_FILE.exists():
        print(f"❌ Erreur : Le fichier source introuvable : {INPUT_FILE}")
        return

    # 1. Chargement avec filtre spatial (Alpes uniquement)
    print(f"📥 Chargement de la zone des Alpes (bbox: {ALPS_BBOX})...")
    # L'option bbox permet de ne pas charger la planète entière en RAM
    gdf = gpd.read_file(INPUT_FILE, bbox=ALPS_BBOX)
    
    nb_initial = len(gdf)
    print(f"✅ {nb_initial} glaciers trouvés dans la zone des Alpes.")

    if nb_initial == 0:
        print("Arrêt : Aucun glacier trouvé dans cette zone.")
        return

    # 2. Filtrage par surface (Enlever les névés)
    print(f"🧹 Suppression des glaciers < {MIN_AREA_KM2} km²...")
    
    # RGI v7 utilise généralement 'area_km2', on vérifie pour être sûr
    col_area = 'area_km2' if 'area_km2' in gdf.columns else 'Area'
    
    if col_area not in gdf.columns:
        print(f"❌ Erreur : Colonne de surface introuvable. Colonnes disponibles : {gdf.columns}")
        return

    gdf_filtre = gdf[gdf[col_area] >= MIN_AREA_KM2]
    nb_final = len(gdf_filtre)
    
    print(f"✅ Filtre appliqué. Glaciers restants : {nb_final} (soit {nb_initial - nb_final} névés retirés).")

    # 3. Sauvegarde
    print("💾 Sauvegarde du nouveau fichier optimisé...")
    
    # Création du dossier cible s'il n'existe pas
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarde en format Shapefile
    gdf_filtre.to_file(OUTPUT_FILE)
    
    # Vérification du poids final
    poids_mo = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    print(f"🎉 Terminé ! Le fichier est prêt : {OUTPUT_FILE} (Taille estimée : {poids_mo:.2f} Mo)")

if __name__ == "__main__":
    process_rgi()