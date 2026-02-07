import requests
import json
import os
from http.server import BaseHTTPRequestHandler

def get_env_or_param(key, params):
    """Récupère une variable depuis l'environnement ou les paramètres"""
    return os.environ.get(key) or params.get(key)

def calculate_stats(records):
    """Calcule les statistiques depuis les records Grist"""
    total = len(records)
    
    # Avis complétés : Avis_Instructeur non vide
    avis_completed = len([r for r in records 
                         if r['fields'].get('Avis_Instructeur', '').strip()])
    
    # À synchroniser : Envoi_DN vide OU commence par "Échec"
    pending = len([r for r in records 
                   if not r['fields'].get('Envoi_DN') 
                   or r['fields'].get('Envoi_DN', '').startswith('Échec')])
    
    # Succès : Envoi_DN = "Succès"
    success = len([r for r in records 
                   if r['fields'].get('Envoi_DN') == 'Succès'])
    
    # Échec : Envoi_DN commence par "Échec"
    error = len([r for r in records 
                 if r['fields'].get('Envoi_DN', '').startswith('Échec')])
    
    return {
        'total': total,
        'pending': pending,
        'success': success,
        'error': error,
        'avisCompleted': avis_completed
    }

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Permettre les requêtes cross-origin (CORS)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Parser les query parameters
            from urllib.parse import urlparse, parse_qs
            query_components = parse_qs(urlparse(self.path).query)
            
            params = {
                'gristDocId': query_components.get('gristDocId', [None])[0],
                'gristTableId': query_components.get('gristTableId', [None])[0],
                'gristAccessToken': query_components.get('gristAccessToken', [None])[0],
                'gristServer': query_components.get('gristServer', [None])[0]
            }
            
            # Récupérer les configurations
            grist_server = get_env_or_param('GRIST_SERVER', params)
            grist_doc_id = get_env_or_param('GRIST_DOC_ID', params)
            grist_table_id = get_env_or_param('GRIST_TABLE_ID', params)
            grist_token = get_env_or_param('GRIST_API_TOKEN', params)
            
            # Construire l'URL de l'API Grist
            api_url = f"{grist_server}/api/docs/{grist_doc_id}/tables/{grist_table_id}/records"
            
            headers = {
                "Authorization": f"Bearer {grist_token}",
                "Content-Type": "application/json"
            }
            
            # Récupérer les données depuis Grist
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            records = data.get('records', [])
            
            # Calculer les stats
            stats = calculate_stats(records)
            
            # Réponse
            self.wfile.write(json.dumps({
                'success': True,
                'stats': stats
            }).encode())
            
        except Exception as e:
            # Réponse erreur
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e)
            }).encode())
    
    def do_OPTIONS(self):
        # Gérer les requêtes preflight CORS
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
