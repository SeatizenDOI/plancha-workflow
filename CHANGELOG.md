# 28/04/2024

Remplacement de tous les os.system. Utilisation de fonction python ou appel avec subprocess

# 09/04/2024

Changement du module reach M2 sur ASV01 car l'ancien avait un problème avec le network. Tous les fichiers sont copiés sur un disque dur.

# 02/2024 

Changement de la carte qui commande l'echosondeur sur ASV02 => Toujours un problème de boot avec la pixwak.

# 07/11/2023


* **CHANGEMENT MAJEUR**: ajout d'un champ dans le plancha_config.json. Si l'option sessions_from_csv est renseigné par le nom d'un fichier, les relevés vont de venir de ce fichier.

* Création d'un dossier qui regroupe les anciens morceaux de code. Modifications des imports pour enlever les erreurs mais pas testés.
* Création d'un dossier qui centralise les fichiers ppk_config
* Changement de la ligne 4: `pos1-frequency: l1+l3+l5` en `pos1-frequency: 3` dans un ppk_config_file.conf
* Création d'un dossier lib qui comprends toutes les librairies crée (lib_dcim, lib_bathy, ...)

* Création d'un fichier lib_tools. Ce fichier ne contient que des fonctions ne dépendant pas de d'autres fonctions :
    - print_plancha_header
    - clear_processed_session
    - create_new_session_folder
    - get_alpha_3_code_from_folder => Non utilisé
    - replace_comma_by_dot
    - replace_line
    - llh_to_txt
    - pos_to_llh

* Création d'un fichier lib_gps. Centralise les fonctions liés au GPS.
    - GPS_position_accuracy
    - download_rgp
    - ppk
    - compute_gps

* Création d'un fichier lib_plot. Permet de décortiquer la fonction GPS_position_accuracy
    - plot_gps_quality
    - plot_standard_deviation_north
    - plot_standard_deviation_east

* Le fichier lib_dcim contient maintenant plus que 3 fonctions :
    - split_videos
    - write_session_info
    - time_calibration_and_geotag