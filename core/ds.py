"""
Module pour les interactions avec Démarches Simplifiées (DS)
"""
import requests

DS_API_URL = "https://demarche.numerique.gouv.fr/api/v2/graphql"


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
    """Cherche le champ DS correspondant à ce block_row_id_annotations"""
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
    
    for row in repetition['rows']:
        if row['id'] == block_row_id:
            return row['champs'][0]['id']
    
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
    """Remplit une ligne dans DS avec une valeur"""
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
