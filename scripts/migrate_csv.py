import pandas as pd
import uuid
import re

def slugify(text):
    """Transforme 'Mer de Glace' en 'mer-de-glace'"""
    return re.sub(r'[^a-z0-9]+', '-', str(text).lower()).strip('-')

print("Lecture de l'ancien CSV...")

try:
    # Lecture du fichier
    df = pd.read_csv("data/glacier_inventory.csv")
    new_rows = []

    # On groupe les paires par nom pour recréer la structure
    for name, group in df.groupby('name'):
        old = group[group['state'] == 'old']
        new = group[group['state'] == 'new']
        
        # On vérifie qu'on a bien une photo 'old' et une 'new' pour ce nom
        if not old.empty and not new.empty:
            pair_id = uuid.uuid4().hex[:6]
            slug = slugify(name)
            
            new_rows.append({
                "pair_id": f"{slug}_{pair_id}",
                "glacier_name": name,
                "lat": new.iloc[0]['lat_photo'],
                "lon": new.iloc[0]['lon_photo'],
                "year_old": old.iloc[0]['date'],
                "year_new": new.iloc[0]['date'],
                "img_old_path": old.iloc[0]['filename'],
                "img_new_path": new.iloc[0]['filename'],
                "contributor": "Guillem"
            })

    # Création du nouveau DataFrame
    new_df = pd.DataFrame(new_rows)
    
    # Sauvegarde
    new_df.to_csv("data/glacier_inventory.csv", index=False)
    print("✅ Migration terminée avec succès !")
    print(f"Nombre de paires créées : {len(new_df)}")

except Exception as e:
    print(f"❌ Erreur lors de la migration : {e}")