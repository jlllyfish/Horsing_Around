from http.server import BaseHTTPRequestHandler
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.grist import get_all_grist_records
from core.stats import calculate_stats

def get_env_or_param(key, params):
    return os.environ.get(key) or params.get(key)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            from urllib.parse import urlparse, parse_qs
            query_components = parse_qs(urlparse(self.path).query)
            
            params = {
                'gristDocId': query_components.get('gristDocId', [None])[0],
                'gristTableId': query_components.get('gristTableId', [None])[0],
                'gristAccessToken': query_components.get('gristAccessToken', [None])[0],
                'gristServer': query_components.get('gristServer', [None])[0]
            }
            
            grist_server = get_env_or_param('GRIST_SERVER', params)
            grist_doc_id = get_env_or_param('GRIST_DOC_ID', params)
            grist_table_id = get_env_or_param('GRIST_TABLE_ID', params)
            grist_token = get_env_or_param('GRIST_API_TOKEN', params)
            
            records = get_all_grist_records(grist_server, grist_doc_id, grist_table_id, grist_token)
            stats = calculate_stats(records)
            
            self.wfile.write(json.dumps({
                'success': True,
                'stats': stats
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
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
