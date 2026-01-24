import requests
import json
import os
from datetime import datetime
from collections import defaultdict
import time
from http.server import BaseHTTPRequestHandler

# Configuration
DS_API_URL = "https://demarche.numerique.gouv.fr/api/v2/graphql"

def get_env_or_param(key, params):
    """Récupère une variable depuis l'environnement ou les paramètres"""
    return os.environ.get(key) or params.get(key)

def get_grist_data(grist_server, grist_doc_id, grist_table_id, grist_token):
    """Récupère les données depuis Grist"""
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

def get_dossier_id_from_number(dossier_number, ds_token):
    """Récupère le vrai dossier_id base64 depuis le numéro"""
    query = """
    query getDossier($dossierNumber: Int!) {
      dossier(number: $dossierNumber) {
        id
      }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {ds_token}",
        "Content-Type": "application/json"
    }
    
    variables = {"dossierNumber": dossier_number}
    response = requests.post(DS_API_URL, headers=headers,
                           json={"query": query, "variables": variables})
    result = response.json()
    
    if result.get('errors') or not result.get('data', {}).get('dossier'):
        return None
    
    return result['data']['dossier']['id']

def check_if_data_exists(dossier_number, repetition_champ_id, donnees_dn, ds_token):
    """Vérifie si les données existent déjà dans le champ répétable"""
    query = """
    query getDossier($dossierNumber: Int!) {
      dossier(number: $dossierNumber) {
        annotations {
          id
          ... on RepetitionChamp {
            rows {
              champs {
                id
                stringValue
              }
            }
          }
        }
      }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {ds_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(DS_API_URL, headers=headers,
                           json={"query": query, "variables": {"dossierNumber": dossier_number}})
    result = response.json()
    
    if result.get('errors') or not result.get('data'):
        return False
    
    annotations = result['data']['dossier']['annotations']
    repetition = next((a for a in annotations if a['id'] == repetition_champ_id), None)
    
    if not repetition or 'rows' not in repetition:
        return False
    
    for row in repetition['rows']:
        for champ in row['champs']:
            if champ['stringValue'] == donnees_dn:
                return True
    
    return False

def get_first_empty_row(dossier_number, repetition_champ_id, ds_token):
    """Retourne l'ID du premier champ vide dans le champ répétable"""
    query = """
    query getDossier($dossierNumber: Int!) {
      dossier(number: $dossierNumber) {
        annotations {
          id
          ... on RepetitionChamp {
            rows {
              champs {
                id
                stringValue
              }
            }
          }
        }
      }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {ds_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(DS_API_URL, headers=headers,
                           json={"query": query, "variables": {"dossierNumber": dossier_number}})
    result = response.json()
    
    if result.get('errors') or not result.get('data'):
        return None
    
    annotations = result['data']['dossier']['annotations']
    repetition = next((a for a in annotations if a['id'] == repetition_champ_id), None)
    
    if not repetition or 'rows' not in repetition:
        return None
    
    for row in repetition['rows']:
        all_empty = all(champ['stringValue'] == '' for champ in row['champs'])
        if all_empty:
            return row['champs'][0]['id']
    
    return None

def find_existing_row_by_block_id(dossier_number, repetition_champ_id, block_row_id, ds_token):
    """Cherche le champ DS correspondant à ce block_row_id Grist"""
    query = """
    query getDossier($dossierNumber: Int!) {
      dossier(number: $dossierNumber) {
        annotations {
          id
          ... on RepetitionChamp {
            rows {
              id
              champs {
                id
              }
            }
          }
        }
      }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {ds_token}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(DS_API_URL, headers=headers,
                           json={"query": query, "variables": {"dossierNumber": dossier_number}})
    result = response.json()
    
    if result.get('errors') or not result.get('data'):
        return None
    
    annotations = result['data']['dossier']['annotations']
    repetition = next((a for a in annotations if a['id'] == repetition_champ_id), None)
    
    if not repetition or 'rows' not in repetition:
        return None
    
    # Chercher la row avec cet ID
    for row in repetition['rows']:
        if row['id'] == block_row_id:
            return row['champs'][0]['id']  # Retourner l'ID du champ à mettre à jour
    
    return None

def add_line_to_ds(dossier_id, instructeur_id, champ_repetable_id, ds_token):
    """Ajoute une ligne vide dans DS"""
    mutation = """
    mutation ajouterLigne($input: DossierModifierAnnotationAjouterLigneInput!) {
      dossierModifierAnnotationAjouterLigne(input: $input) {
        annotation {
          id
          ... on RepetitionChamp {
            rows {
              id
              champs {
                id
                stringValue
              }
            }
          }
        }
        errors {
          message
        }
      }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {ds_token}",
        "Content-Type": "application/json"
    }
    
    variables = {
        "input": {
            "dossierId": dossier_id,
            "instructeurId": instructeur_id,
            "annotationId": champ_repetable_id
        }
    }
    
    response = requests.post(DS_API_URL, headers=headers, 
                           json={"query": mutation, "variables": variables})
    return response.json()

def fill_line_in_ds(dossier_id, instructeur_id, champ_id, value, ds_token):
    """Remplit la ligne créée avec une valeur"""
    mutation = """
    mutation modifierAnnotation($input: DossierModifierAnnotationTextInput!) {
      dossierModifierAnnotationText(input: $input) {
        annotation {
          id
          stringValue
        }
        errors {
          message
        }
      }
    }
    """
    
    headers = {
        "Authorization": f"Bearer {ds_token}",
        "Content-Type": "application/json"
    }
    
    variables = {
        "input": {
            "dossierId": dossier_id,
            "instructeurId": instructeur_id,
            "annotationId": champ_id,
            "value": value
        }
    }
    
    response = requests.post(DS_API_URL, headers=headers,
                           json={"query": mutation, "variables": variables})
    return response.json()

def update_grist_status(record_id, success, message, grist_server, grist_doc_id, grist_table_id, grist_token):
    """Met à jour le statut dans Grist"""
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

def process_record_with_retry(dossier_id, dossier_number, record_id, donnees_dn, block_row_id,
                              ds_token, instructeur_id, champ_repetable_id,
                              grist_server, grist_doc_id, grist_table_id, grist_token,
                              max_retries=3, delay=5):
    """Traite un record avec retry automatique"""
    
    for attempt in range(1, max_retries + 1):
        try:
            # 1. Chercher si cette ligne existe déjà dans DS (via block_row_id)
            existing_champ_id = None
            if block_row_id:
                print(f"  🔍 Recherche block_row_id: {block_row_id}")
                existing_champ_id = find_existing_row_by_block_id(
                    dossier_number, champ_repetable_id, block_row_id, ds_token
                )
                 print(f"  📍 Résultat recherche: {existing_champ_id}")
            if existing_champ_id:
                # Mettre à jour la ligne existante
                print(f"  🔄 Mise à jour ligne existante pour record {record_id} (tentative {attempt}/{max_retries})")
                result_fill = fill_line_in_ds(dossier_id, instructeur_id, existing_champ_id, donnees_dn, ds_token)
            else:
                # Vérifier si données existent déjà (par contenu)
                if check_if_data_exists(dossier_number, champ_repetable_id, donnees_dn, ds_token):
                    print(f"  ℹ️  Record {record_id}: données déjà présentes dans DS, skipping")
                    update_grist_status(record_id, True, "", grist_server, grist_doc_id, grist_table_id, grist_token)
                    return True
                
                # Vérifier s'il y a une ligne vide disponible
                empty_row_id = get_first_empty_row(dossier_number, champ_repetable_id, ds_token)
                
                if empty_row_id:
                    print(f"  📝 Utilisation ligne vide existante pour record {record_id} (tentative {attempt}/{max_retries})")
                    result_fill = fill_line_in_ds(dossier_id, instructeur_id, empty_row_id, donnees_dn, ds_token)
                else:
                    print(f"  ➕ Création nouvelle ligne pour record {record_id} (tentative {attempt}/{max_retries})")
                    result_add = add_line_to_ds(dossier_id, instructeur_id, champ_repetable_id, ds_token)
                    
                    if result_add.get('errors'):
                        raise Exception(f"Erreur GraphQL: {result_add['errors']}")
                    
                    mutation_result = result_add['data']['dossierModifierAnnotationAjouterLigne']
                    if mutation_result.get('errors'):
                        raise Exception(f"Erreur mutation: {mutation_result['errors']}")
                    
                    rows = mutation_result['annotation']['rows']
                    new_champ_id = rows[-1]['champs'][0]['id']
                    result_fill = fill_line_in_ds(dossier_id, instructeur_id, new_champ_id, donnees_dn, ds_token)
            
            # Vérifier le remplissage
            if result_fill.get('errors'):
                raise Exception(f"Erreur GraphQL: {result_fill['errors']}")
            
            mutation_fill = result_fill['data']['dossierModifierAnnotationText']
            if mutation_fill.get('errors'):
                raise Exception(f"Erreur remplissage: {mutation_fill['errors']}")
            
            update_grist_status(record_id, True, "", grist_server, grist_doc_id, grist_table_id, grist_token)
            return True
            
        except Exception as e:
            if attempt < max_retries:
                time.sleep(delay)
            else:
                update_grist_status(record_id, False, str(e), grist_server, grist_doc_id, grist_table_id, grist_token)
                return False

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Lire le body de la requête
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            params = json.loads(body.decode('utf-8'))
            
            # Récupérer les configurations
            grist_server = get_env_or_param('GRIST_SERVER', params)
            grist_doc_id = get_env_or_param('GRIST_DOC_ID', params) or params.get('gristDocId')
            grist_table_id = get_env_or_param('GRIST_TABLE_ID', params) or params.get('gristTableId')
            grist_token = get_env_or_param('GRIST_API_TOKEN', params) or params.get('gristAccessToken')
            
            ds_token = get_env_or_param('DS_API_TOKEN', params)
            instructeur_id = get_env_or_param('DS_INSTRUCTEUR_ID', params)
            champ_repetable_id = get_env_or_param('DS_CHAMP_REPETABLE_ID', params)
            
            # Récupérer les données à traiter
            enfants = get_grist_data(grist_server, grist_doc_id, grist_table_id, grist_token)
            
            if not enfants:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'success': True,
                    'processed': 0,
                    'message': 'Aucune ligne à traiter'
                }).encode())
                return
            
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
                        continue
                    
                    for enfant in records:
                        record_id = enfant['id']
                        donnees_dn = enfant['fields'].get('Donnees_DN')
                        block_row_id = enfant['fields'].get('block_row_id')
                        
                        if not donnees_dn:
                            continue
                        
                        if process_record_with_retry(
                            dossier_id, dossier_number, record_id, donnees_dn, block_row_id,
                            ds_token, instructeur_id, champ_repetable_id,
                            grist_server, grist_doc_id, grist_table_id, grist_token
                        ):
                            processed += 1
                
                except Exception as e:
                    continue
            
            # Réponse succès
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'processed': processed,
                'message': f'{processed} ligne(s) traitée(s)'
            }).encode())
            
        except Exception as e:
            # Réponse erreur
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': False,
                'error': str(e)
            }).encode())
