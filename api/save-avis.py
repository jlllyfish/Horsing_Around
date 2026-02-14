import requests
import json
import os
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Lire le body de la requête
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            params = json.loads(body.decode('utf-8'))
            
            # Récupérer les paramètres
            record_id = params.get('recordId')
            avis = params.get('avis')
            table_id = params.get('tableId') or 'Demarche_138030_repetable_enfant'
            
            if not record_id:
                raise ValueError("recordId is required")
            if not avis:
                raise ValueError("avis is required")
            
            # Récupérer les configurations
            grist_server = os.environ.get('GRIST_SERVER') or params.get('gristServer')
            grist_doc_id = os.environ.get('GRIST_DOC_ID') or params.get('gristDocId')
            
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
            
            # Préparer les données à envoyer
            data = {
                "records": [{
                    "id": record_id,
                    "fields": {
                        "Avis_commission": avis
                    }
                }]
            }
            
            # Mettre à jour le record dans Grist
            response = requests.patch(api_url, headers=headers, json=data)
            response.raise_for_status()
            
            # Réponse succès
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'message': 'Avis enregistré avec succès'
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
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()