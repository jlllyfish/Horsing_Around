"""
Module pour la logique de traitement des records
"""
import time
from .grist import update_grist_status, update_grist_block_row_id
from .ds import (
    check_if_data_exists,
    find_existing_row_by_block_id,
    get_first_empty_row,
    add_line_to_ds,
    fill_line_in_ds
)


def process_record_with_retry(dossier_id, dossier_number, record_id, donnees_dn, block_row_id_annotations,
                              ds_token, instructeur_id, champ_repetable_id,
                              grist_server, grist_doc_id, grist_table_id, grist_token,
                              max_retries=3, delay=5):
    """Traite un record avec retry automatique"""
    print(f"\n🔍 DEBUG Record {record_id}:")
    print(f"   Donnees_DN: {donnees_dn}")
    print(f"   block_row_id: {block_row_id_annotations}")

    for attempt in range(1, max_retries + 1):
        try:
            # 1. Chercher si cette ligne existe déjà dans DS (via block_row_id_annotations)
            existing_champ_id = None
            if block_row_id_annotations:
                print(f"  🔍 Recherche block_row_id_annotations: {block_row_id_annotations}")
                existing_champ_id = find_existing_row_by_block_id(
                    dossier_number, champ_repetable_id, block_row_id_annotations, ds_token
                )
                print(f"  📍 Résultat recherche: {existing_champ_id}")
            
            if existing_champ_id:
                print(f"  📝 UPDATE ligne existante - Champ ID: {existing_champ_id}")
                print(f"  📝 Valeur à écrire: {donnees_dn}")
                result_fill = fill_line_in_ds(dossier_id, instructeur_id, existing_champ_id, donnees_dn, ds_token)
                print(f"  ✅ Résultat update: {result_fill}")
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
                    new_row_id = rows[-1]['id']  # L'ID de la row DS créée
                    new_champ_id = rows[-1]['champs'][0]['id']
                    
                    # Stocker le row_id DS dans Grist
                    print(f"  💾 Stockage row_id DS dans Grist: {new_row_id}")
                    update_grist_block_row_id(record_id, new_row_id, grist_server, grist_doc_id, grist_table_id, grist_token)
                    
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
