from http.server import BaseHTTPRequestHandler
import json
import sys
import os

# Ajouter le dossier parent au path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.processor import process_record_with_retry
from core.grist import get_grist_data
from core.ds import get_dossier_id_from_number
from collections import defaultdict

def get_env_or_param(key, params):
    return os.environ.get(key) or params.get(key)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            params = json.loads(body.decode('utf-8'))
            
            grist_server = get_env_or_param('GRIST_SERVER', params)
            grist_doc_id = get_env_or_param('GRIST_DOC_ID', params) or params.get('gristDocId')
            grist_table_id = get_env_or_param('GRIST_TABLE_ID', params) or params.get('gristTableId')
            grist_token = get_env_or_param('GRIST_API_TOKEN', params) or params.get('gristAccessToken')
            
            ds_token = get_env_or_param('DS_API_TOKEN', params)
            instructeur_id = get_env_or_param('DS_INSTRUCTEUR_ID', params)
            champ_repetable_id = get_env_or_param('DS_CHAMP_REPETABLE_ID', params)
            
            enfants = get_grist_data(grist_server, grist_doc_id, grist_table_id, grist_token)
            
            if not enfants:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'processed': 0,
                    'message': 'Aucune ligne à traiter'
                }).encode())
                return
            
            dossiers_groups = defaultdict(list)
            for enfant in enfants:
                dossier_number = enfant['fields'].get('dossier_number')
                if dossier_number:
                    try:
                        dossiers_groups[int(dossier_number)].append(enfant)
                    except ValueError:
                        pass
            
            processed = 0
            
            for dossier_number, records in dossiers_groups.items():
                try:
                    dossier_id = get_dossier_id_from_number(dossier_number, ds_token)
                    if not dossier_id:
                        continue
                    
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
                    continue
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'processed': processed,
                'message': f'{processed} ligne(s) traitée(s)'
            }).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e)
            }).encode())
