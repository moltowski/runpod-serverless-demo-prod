#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Récupère l'output d'un job RunPod et sauvegarde la vidéo
"""
import requests
import sys
import json
import io
import base64
from pathlib import Path
import os

# Fix Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

API_KEY = os.getenv("RUNPOD_API_KEY", "YOUR_API_KEY_HERE")
ENDPOINT_ID = os.getenv("ENDPOINT_ID", "YOUR_ENDPOINT_ID")
OUTPUT_DIR = Path(__file__).parent / "outputs"

def get_job_output(job_id):
    """Récupère l'output d'un job et sauvegarde la vidéo"""
    url = f"https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{job_id}"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    print("=" * 70)
    print(f"📡 Récupération job {job_id}")
    print("=" * 70)
    
    try:
        resp = requests.get(url, headers=headers)
        
        if resp.status_code != 200:
            print(f"❌ Erreur {resp.status_code}: {resp.text}")
            return
        
        data = resp.json()
        status = data.get('status')
        
        print(f"📊 Status: {status}")
        
        if status != 'COMPLETED':
            print(f"⏳ Job pas encore terminé (status: {status})")
            return
        
        # Vérifier l'output
        output = data.get('output', {})
        
        if not isinstance(output, dict):
            print(f"❌ Output invalide: {output}")
            return
        
        # Afficher les infos
        print(f"✅ Status: {output.get('status')}")
        print(f"📝 Message: {output.get('message')}")
        print(f"⏱️  Execution time: {data.get('executionTime', 0)}ms")
        
        # Récupérer les fichiers
        outputs_data = output.get('outputs', [])
        
        if not outputs_data:
            print("❌ Aucun fichier de sortie trouvé")
            return
        
        print(f"\n📦 {len(outputs_data)} fichier(s) trouvé(s):")
        
        # Créer le dossier outputs
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        saved_files = []
        
        for i, file_data in enumerate(outputs_data, 1):
            filename = file_data.get('filename', f'output_{i}.mp4')
            file_type = file_data.get('type', 'unknown')
            data_b64 = file_data.get('data')
            
            if not data_b64:
                print(f"  ⚠️  {filename}: Pas de données")
                continue
            
            print(f"  📹 {filename} ({file_type})")
            
            # Décoder et sauvegarder
            try:
                file_bytes = base64.b64decode(data_b64)
                output_path = OUTPUT_DIR / filename
                
                with open(output_path, 'wb') as f:
                    f.write(file_bytes)
                
                file_size = len(file_bytes) / (1024 * 1024)  # MB
                print(f"     ✅ Sauvegardé: {output_path} ({file_size:.2f} MB)")
                saved_files.append(str(output_path))
                
            except Exception as e:
                print(f"     ❌ Erreur sauvegarde: {e}")
        
        if saved_files:
            print(f"\n🎉 {len(saved_files)} fichier(s) sauvegardé(s) dans {OUTPUT_DIR.absolute()}")
            for path in saved_files:
                print(f"   • {path}")
        
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python download_job_output.py <job_id>")
        print("\nExemple:")
        print("  python download_job_output.py 94bfe8e4-80a2-406e-882d-bf0f27b303f2-e2")
        print("\nLe fichier sera sauvegardé dans ./outputs/")
        sys.exit(1)
    
    job_id = sys.argv[1]
    get_job_output(job_id)
