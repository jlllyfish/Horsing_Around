"""
Module pour les interactions avec Grist
"""
import requests
from datetime import datetime


def get_grist_data(grist_server, grist_doc_id, grist_table_id, grist_token):
    """Récupère les données depuis Grist à synchroniser"""
    api_url = f"{grist_server}/api/docs/{grist_doc_id}/tables/{grist_table_id}/records"
    
    headers = {
        "Authorization": f"Bearer {grist_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    all_records = data.get('records', [])
    
    # Filtrer : Envoi_DN vide OU commence par "Échec"
    enfants = [r for r in all_records 
               if not r['fields'].get('Envoi_DN') 
               or r['fields'].get('Envoi_DN', '').startswith('Échec')]
    
    return enfants


def get_all_grist_records(grist_server, grist_doc_id, grist_table_id, grist_token):
    """Récupère TOUS les records Grist (pour stats)"""
    api_url = f"{grist_server}/api/docs/{grist_doc_id}/tables/{grist_table_id}/records"
    
    headers = {
        "Authorization": f"Bearer {grist_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    
    data = response.json()
    return data.get('records', [])


def update_grist_status(record_id, success, message, grist_server, grist_doc_id, grist_table_id, grist_token):
    """Met à jour le statut Envoi_DN et Date_envoi_DN dans Grist"""
    fields = {
        "Envoi_DN": "Succès" if success else f"Échec: {message}"
    }
    
    if success:
        fields["Date_envoi_DN"] = datetime.now().isoformat()
    
    api_url = f"{grist_server}/api/docs/{grist_doc_id}/tables/{grist_table_id}/records"
    
    headers = {
        "Authorization": f"Bearer {grist_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "records": [{
            "id": record_id,
            "fields": fields
        }]
    }
    
    response = requests.patch(api_url, headers=headers, json=data)
    return response.json()


def update_grist_block_row_id(record_id, block_row_id, grist_server, grist_doc_id, grist_table_id, grist_token):
    """Met à jour le block_row_id_annotations dans Grist"""
    fields = {
        "block_row_id_annotations": block_row_id
    }
    
    api_url = f"{grist_server}/api/docs/{grist_doc_id}/tables/{grist_table_id}/records"
    
    headers = {
        "Authorization": f"Bearer {grist_token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "records": [{
            "id": record_id,
            "fields": fields
        }]
    }
    
    response = requests.patch(api_url, headers=headers, json=data)
    return response.json()
