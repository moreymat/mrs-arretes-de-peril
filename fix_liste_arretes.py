"""Corrige la liste d'arrêtés.

Corrections manuelles pour pallier les erreurs du site et éviter les corrections en aval.
"""
import argparse
from pathlib import Path
import os.path

import pandas as pd

# chaque arrondissement a un code postal
ART_CP = [("1er arrondissement", "13001")] + [
    ("{}ème arrondissement".format(i), "130{:02}".format(i)) for i in range(2, 17)
]
ART2CP = dict(ART_CP)
CP2ART = {code_postal: arr for (arr, code_postal) in ART_CP}

# dictionnaire de corrections manuelles
MANUAL_FIX_URL = {
    # j'ai réussi à retrouver la bonne URL
    "https://www.marseille.fr/logement-urbanisme/am%C3%A9lioration-de-lhabitat/sites/default/files/contenu/logement/Mains_Levees/ml_8-rue-de-jemmapes-13001_2019_03216_vdm.pdf": "https://www.marseille.fr/sites/default/files/contenu/logement/Mains_Levees/ml_8-rue-de-jemmapes-13001_2019_03216_vdm.pdf",
    # idem, la bonne URL était enchassée dans une autre
    "https://www.marseille.fr/https://www.marseille.fr/sites/default/files/contenu/logement/Arretes-peril/6-rue-de-la-butte-13002_2019_01932.pdf/default/files/contenu/logement/Arretes-deconstruction/deconstruction_8-rue-de-la-butte-13002_2019_03064_vdm.pdf": "https://www.marseille.fr/sites/default/files/contenu/logement/Arretes-peril/6-rue-de-la-butte-13002_2019_01932.pdf",
    # un "logement/" de trop
    "https://www.marseille.fr/sites/default/files/contenu/logement/logement/Mains_Levees/35-rue-de-lodi-13005_2019_01521.pdf": "https://www.marseille.fr/sites/default/files/contenu/logement/Mains_Levees/35-rue-de-lodi-13005_2019_01521.pdf",
    # je n'ai pas la bonne URL
    "https://www.marseille.fr/logement-urbanisme/am%C3%A9lioration-de-lhabitat/PI_53-rue-roger-renzo-13008_2020_02689_VDM.pdf": "",
}

# TODO correction d'adresses automatique ?
MANUAL_FIX_ADRESSE = {
    "49 rue Pierre Albran": "49 rue Pierre Albrand",
}

# dépendance fonctionnelle adresse -> code postal
MANUAL_ADRESSE_TO_CP = {
    # une occurrence dans 13002 (ok) et une 13004 (pas ok) (et c'est "Pierre Albrand")
    # mais une seule vraie occurrence car c'est la même URL !
    "49 rue Pierre Albrand": "13002",
    # une occurrence dans 13005 (ok) et une 13006 (pas ok)
    "16 rue de Bruys": "13005",
    # deux occurrences dans 13006 (ok) et une dans 13005 (pas ok)
    "35 rue de Lodi": "13006",
    # 13005 (faux) et 13006 (vrai)
    "59 place Jean Jaurès": "13006",
    # 13004 (faux) et 13001 (vrai)
    "2 rue d'Anvers": "13001",
}

# dépendance manuelle item -> adresse
MANUAL_ITEM_TO_ADRESSE = {
    "Arrêté modificatif de péril ordinaire - 20 rue du Jet d'eau": "20 rue du Jet d'eau",
    "Arrêté portant mise en place d'un périmètre de sécurité sur la rue d'Aubagne et la rue Jean Roque": "rue d'Aubagne et rue Jean Roque",
    "Arrêté portant sur la modification du périmètre de sécurité sur la rue d'Aubagne": "rue d'Aubagne",
    "Arrêté modifiant le périmètre de sécurité de la rue d'Aubagne et de la rue Jean Roque - 13001 2019_01380_VDM du 25/04/19": "rue d'Aubagne et rue Jean Roque",
    "Arrêté portant sur la mise en place d'un périmètre de sécurité pour l'immeuble CG13 situé rue Saint-Cassien et Bouleverd Louis de Grasse - 13002": "rue Saint-Cassien et Boulevard Louis de Grasse",
    "Arrêté de police 20 rue de l'Académie - 13001 - abrogation du 08/10/2020": "20 rue de l'Académie",  # x2
    "Arrêté de police générale du Maire portant  sur le 54 rue d'Italie - 13006": "54 rue d'Italie",
    "Arrêté portant sur la mise en place d'un périmètre de sécurité sur la rue Curiol (N°79, 81, 85, 92, 94, 96, 98 et 100) et la place Jean Jaurès (n°24 et 26)": "rue Curiol (N°79, 81, 85, 92, 94, 96, 98 et 100) et place Jean Jaurès (n°24 et 26)",
}


def apply_manual_fixes(df, verbose=False):
    """Applique des corrections manuelles à certaines entrées.

    Idéalement, certaines corrections devraient être (semi-)automatisées.
    """
    # corrections directement dans une colonne (remplacement simple)
    for adr_bad, adr_fix in MANUAL_FIX_ADRESSE.items():
        df.loc[df["adresse"] == adr_bad, "adresse"] = adr_fix
    for url_bad, url_fix in MANUAL_FIX_URL.items():
        df.loc[df["url"] == url_bad, "url"] = url_fix
    # corrections dépendantes d'une autre colonne :
    # - correction dépendante manuelle (TODO vérifier si encore utile 2021-07)
    for e_item, e_adrs in MANUAL_ITEM_TO_ADRESSE.items():
        df.loc[df["item"] == e_item, "adresse"] = e_adrs
    # - correction correspondant à une dépendance fonctionnelle
    for e_adr, e_cp in MANUAL_ADRESSE_TO_CP.items():
        df.loc[df["adresse"] == e_adr, "code_postal"] = e_cp
        df.loc[df["adresse"] == e_adr, "arrondissement"] = CP2ART[e_cp]
    # corrections plus complexes :
    # - re-créer 1 ligne correcte à partir de 2 lignes incorrectes
    df.loc[
        (
            (df["adresse"] == "22 rue Toussaint")
            & (df["nom_doc"] == "Main levée du 05/06/2019")
        ),
        "url",
    ] = "https://www.marseille.fr/sites/default/files/contenu/logement/Arretes-peril/22-rue-toussaint-13003-ml-_pgi_2019_01717-22_vdm.pdf"
    df.drop(
        df.loc[((df["adresse"] == "22 rue Toussaint") & df["nom_doc"].isna())].index,
        inplace=True,
    )
    #
    return df


def clean(df, verbose=False):
    """Nettoie le tableau de données"""
    # on supprime les URLs qui ne pointent pas vers le site de la ville
    if verbose:
        print("Suppression des URLs : pas sur le site de la ville")
        print(df.loc[~df["url"].str.contains("marseille.fr"), "url"])
    df.loc[~df["url"].str.contains("marseille.fr"), "url"] = ""
    # on supprime les URLs qui ne sont pas des PDF
    # ? ou ? quickfix pour 1 URL mal formée (2020-02-27) : url = url + ".pdf"
    if verbose:
        print("Suppression des URLs : pas des PDF")
        print(df.loc[~df["url"].str.endswith(".pdf"), "url"])
    df.loc[~df["url"].str.endswith(".pdf"), "url"] = ""
    #
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "liste_csv", help="Fichier CSV raw contenant la liste des documents"
    )
    args = parser.parse_args()
    # fichier brut => fichier corrigé
    fp_raw = Path(args.liste_csv).resolve()
    fp_fix = fp_raw.parents[1] / "interim" / fp_raw.name
    # on ouvre le fichier bugué
    df = pd.read_csv(fp_raw, dtype="string")
    df = apply_manual_fixes(df, verbose=True)
    df = clean(df, verbose=True)
    # on exporte le dataframe corrigé, en gardant le même format que précemment
    # y compris les retours à la ligne du dialecte Excel du CSV Writer :
    # https://docs.python.org/3/library/csv.html#csv.Dialect.lineterminator
    df.to_csv(fp_fix, sep=",", index=False, line_terminator="\r\n")
