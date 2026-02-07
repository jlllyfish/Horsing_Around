"""
Serveur Flask local pour tester le widget sans Vercel
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
from collections import defaultdict

# Imports depuis les modules core
from core.grist import get_grist_data, get_all_grist_records
from core.ds import get_dossier_id_from_number
from core.processor import process_record_with_retry
from core.stats import calculate_stats

# Charger les variables d'environnement
load_dotenv()

app = Flask(__name__, static_folder='.')
CORS(app)

# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    """Sert la page principale"""
    return send_from_directory('.', 'index.html')


@app.route('/<path:path>')
def static_files(path):
    """Sert les fichiers statiques (CSS, JS, images)"""
    return send_from_directory('.', path)


@app.route('/api/stats', methods=['GET'])
def stats():
    """Récupère les statistiques depuis Grist"""
    try:
        # Récupérer les configurations depuis .env
        grist_server = os.environ.get('GRIST_SERVER')
        grist_doc_id = os.environ.get('GRIST_DOC_ID')
        grist_table_id = os.environ.get('GRIST_TABLE_ID')
        grist_token = os.environ.get('GRIST_API_TOKEN')
        
        # Récupérer tous les records depuis Grist
        records = get_all_grist_records(grist_server, grist_doc_id, grist_table_id, grist_token)

        # Calculer les stats
        stats_data = calculate_stats(records)
        
        return jsonify({
            'success': True,
            'stats': stats_data
        })
        
    except Exception as e:
        print(f"❌ Erreur stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/process', methods=['POST'])
def process():
    """Lance le traitement de synchronisation Grist → DS"""
    try:
        # Récupérer les configurations
        grist_server = os.environ.get('GRIST_SERVER')
        grist_doc_id = os.environ.get('GRIST_DOC_ID')
        grist_table_id = os.environ.get('GRIST_TABLE_ID')
        grist_token = os.environ.get('GRIST_API_TOKEN')
        
        ds_token = os.environ.get('DS_API_TOKEN')
        instructeur_id = os.environ.get('DS_INSTRUCTEUR_ID')
        champ_repetable_id = os.environ.get('DS_CHAMP_REPETABLE_ID')
        
        print("🚀 Démarrage du traitement...")
        
        # Récupérer les données à traiter
        enfants = get_grist_data(grist_server, grist_doc_id, grist_table_id, grist_token)
        
        if not enfants:
            print("ℹ️  Aucune ligne à traiter")
            return jsonify({
                'success': True,
                'processed': 0,
                'message': 'Aucune ligne à traiter'
            })
        
        print(f"📊 {len(enfants)} ligne(s) à traiter")
        
        # Grouper par dossier
        dossiers_groups = defaultdict(list)
        for enfant in enfants:
            dossier_number = enfant['fields'].get('dossier_number')
            if dossier_number:
                try:
                    dossiers_groups[int(dossier_number)].append(enfant)
                except ValueError:
                    pass
        
        processed = 0
        
        # Traiter chaque dossier
        for dossier_number, records in dossiers_groups.items():
            try:
                dossier_id = get_dossier_id_from_number(dossier_number, ds_token)
                if not dossier_id:
                    print(f"❌ Dossier {dossier_number}: ID non trouvé")
                    continue
                
                print(f"🗂️  Traitement dossier {dossier_number} ({len(records)} records)")
                
                for enfant in records:
                    record_id = enfant['id']
                    donnees_dn = enfant['fields'].get('Donnees_DN')
                    block_row_id_annotations = enfant['fields'].get('block_row_id_annotations')
                    
                    if not donnees_dn:
                        continue
                    
                    if process_record_with_retry(
                        dossier_id, dossier_number, record_id, donnees_dn, block_row_id_annotations,
                        ds_token, instructeur_id, champ_repetable_id,
                        grist_server, grist_doc_id, grist_table_id, grist_token
                    ):
                        processed += 1
            
            except Exception as e:
                print(f"❌ Erreur dossier {dossier_number}: {e}")
                continue
        
        print(f"✅ Traitement terminé : {processed} ligne(s) traitée(s)")
        
        return jsonify({
            'success': True,
            'processed': processed,
            'message': f'{processed} ligne(s) traitée(s)'
        })
        
    except Exception as e:
        print(f"❌ Erreur process: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Serveur Flask - Mode développement local")
    print("=" * 60)
    print("📍 URL principale : http://localhost:3000")
    print("📊 API Stats      : http://localhost:3000/api/stats")
    print("⚙️  API Process   : http://localhost:3000/api/process")
    print("=" * 60)
    print("🛑 Arrêter avec Ctrl+C")
    print("=" * 60)
    app.run(debug=True, port=3000, host='0.0.0.0')
