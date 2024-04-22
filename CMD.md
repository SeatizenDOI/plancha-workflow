# Useful command

```bash
    # Scan ip port on network
    sudo nmap -sn 192.168.1.0/24

    # Sync folder 
    sudo rsync --progress -avv /media/bioeos/E/202310_plancha_session/ /media/bioeos/E/202211_plancha_session/ /media/bioeos/E/2021_plancha_session/ /media/bioeos/E/2015_plancha_session/ /media/bioeos/D/202311_plancha_session/ /media/bioeos/D/202312_plancha_session/ /media/bioeos/F/202210_plancha_session/ /media/bioeos/F/202301-07_plancha_session/ /media/bioeos/F/202305_plancha_session/ /media/bioeos/F/202403_plancha_session/  -e "ssh -p 222" Victor@192.168.1.9:/volume1/plancha/

```
# Reach M2

Quand on est connecté en USB, on peut se connecter à 192.168.2.15 et récupérer un zip qui contient un dump des infos de la planche

Si on veut récupéré par USB, on peut aussi se connecter par sftp avec filezilla avec sftp://192.168.2.15 reach emlidreach 22
