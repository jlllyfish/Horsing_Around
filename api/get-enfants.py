import requests
import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

def get_env_or_param(key, params):
    """Récupère une variable depuis l'environnement ou les paramètres"""
    return os.environ.get(key) or params.get(key)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # CORS headers
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Parser les query parameters
            query_components = parse_qs(urlparse(self.path).query)
            
            params = {
                'gristDocId': query_components.get('gristDocId', [None])[0],
                'tableId': query_components.get('tableId', [None])[0],
                'gristServer': query_components.get('gristServer', [None])[0]
            }
            
            # Récupérer les configurations
            grist_server = get_env_or_param('GRIST_SERVER', params)
            grist_doc_id = get_env_or_param('GRIST_DOC_ID', params)
            table_id = params.get('tableId') or 'Demarche_138030_repetable_enfant'
            
            # 🔒 SECURITY: Token MUST come from environment variables only
            grist_token = os.environ.get('GRIST_API_TOKEN')
            if not grist_token:
                raise ValueError("GRIST_API_TOKEN must be set in environment variables")
            
            # Construire l'URL de l'API Grist
            api_url = f"{grist_server}/api/docs/{grist_doc_id}/tables/{table_id}/records"
            
            headers = {
                "Authorization": f"Bearer {grist_token}",
                "Content-Type": "application/json"
            }
            
            # Récupérer les données depuis Grist
            response = requests.get(api_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            records = data.get('records', [])
            
            # Réponse
            self.wfile.write(json.dumps({
                'success': True,
                'records': records
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