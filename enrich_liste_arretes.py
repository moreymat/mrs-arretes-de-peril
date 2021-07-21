"""Enrichit la liste des arrêtés avec des informations extraites de la page du site.

"""


import argparse
from datetime import date
from pathlib import Path
import re

import pandas as pd


def predict_doc_class(doc_text):
    """Prédit la classe d'un document, parmi les 8 possibles.

    Classes :
    * Arrêtés de péril imminent, de Main Levée et de Réintégration partielle,
    * Arrêtés d'insécurité imminente des équipements communs,
    * Arrêtés d'interdiction d'occuper,
    * Arrêtés de police générale,
    * Arrêtés d'évacuation et de réintégration,
    * Diagnostics d'ouvrages,
    * Arrêtés de périmètres de sécurité sur voie publique,
    * Arrêtés de déconstruction

    Parameters
    ----------
    doc_text : str
        Texte du lien vers le doc

    Returns
    -------
    doc_class : str
        Classe du document (legacy)
    """
    if "péril" in doc_text:
        doc_class = (
            "Arrêtés de péril imminent, de Main Levée et de Réintégration partielle"
        )
    elif "insécurité" in doc_text:
        doc_class = "Arrêtés d'insécurité imminente des équipements communs"
    elif "interdiction d'occup" in doc_text.lower():
        doc_class = "Arrêtés d'interdiction d'occuper"
    elif "police générale" in doc_text:
        doc_class = "Arrêtés de police générale"
    elif "évacuation" in doc_text or "réintégration" in doc_text:
        doc_class = "Arrêtés d'évacuation et de réintégration"
    elif "diagnostic d'ouvrages" in doc_text:
        doc_class = "Diagnostics d'ouvrages"
    elif "périmètre de sécurité" in doc_text:
        doc_class = "Arrêtés de périmètres de sécurité sur voie publique"
    elif "déconstruction" in doc_text:
        doc_class = "Arrêtés de déconstruction"
    # heuristique: on considère que toutes les mains-levées sont de péril (classe majoritaire)
    # FIXME faire une vraie prédiction en utilisant le reste de l'item (pas seulement le nom du doc)
    elif "main levée" in doc_text.lower():
        doc_class = (
            "Arrêtés de péril imminent, de Main Levée et de Réintégration partielle"
        )
    # évolution réglementaire 2021
    elif "mise en sécurité urgente" in doc_text:
        doc_class = "Arrêtés de mise en sécurité urgente"
    elif "mise en sécurité" in doc_text:
        doc_class = "Arrêtés de mise en sécurité"
    # classe inconnue => objectif : résorber le nombre d'occurrences
    else:
        doc_class = "?"
    return doc_class


RE_DATE_NOMDOC_Y4 = re.compile(r"(?P<date_link>\d{2}/\d{2}/\d{4})")
RE_DATE_NOMDOC_Y2 = re.compile(r"(?P<date_link>\d{2}/\d{2}/\d{2})")


def extract_date_nomdoc(df, verbose=False):
    """Extrait la date du texte du document"""
    # date au format attendu : dd/mm/yyyy
    df.loc[:, "date_link"] = df["nom_doc"].str.extract(RE_DATE_NOMDOC_Y4, expand=False)
    # date dans une variante courante : dd/mm/yy
    s_date_y2 = (
        df.loc[df["date_link"].isna(), "nom_doc"]
        .str.extract(RE_DATE_NOMDOC_Y2, expand=False)
        .str.rsplit("/", 1, expand=False)
        .str.join("/20")
    )
    df.loc[df["date_link"].isna(), "date_link"] = s_date_y2
    if verbose:
        print("Entrées sans date")
        with pd.option_context("max_colwidth", -1):
            print(df.loc[df["date_link"].isna(), "nom_doc"])
    return df


# FIXME nombreuses corrections => déplacer vers un fichier CSV ?
FIX_DATE_LINK = {
    "mlp_-20-rue-corneille-13001_2019_03747.pdf": "28/10/2019",  # 289/10/2019
    "interdiction_occuper_2-bld-des-dames-13002_2019_02168.pdf": "19/06/2019",  # 289/10/2019
    "pgi_123-123b-rue-de-l-eveche-13002_2019_03385_vdm.pdf": "26/09/2019",  # 30/23/2019
    "10-place-jean-jaures-13001_arrete_modificatif_de_pi-2020_03143_vdm_1.pdf": "27/01/2021",  # "27 janvier 2021"
    "59-place-jean-jaures_13006_arrete_astreinte_2021_01383_22-mai-2021.pdf": "22/05/2021",  # "22 /05/2021"
    "80_rue_nationale_ppm_12_532_15-mars-2013.pdf": "15/03/2013",  # "15 mars 2013"
    "8_rue_de_recolettes_13001_ppm_2021_00525.pdf": "16/02/2021",  # "16 février 2021"
    "55-57-rue-de-rome-13001_2019_01329.pdf": "23/04/2019",  # "23 avril 2019"
    "ppm_3-rue-vacon-13001_2020_00183_vdm.pdf": "23/01/2020",  # "23 /01/2020"
    "ML-24-rue-Vacon-13001_2018_03193.pdf": "06/12/2018",  # "6/12/2018"
    "deconstruction_8-rue-de-la-butte-13002_2019_03064_vdm.pdf": "30/08/2019",  # "30/008/2019"
    "ml_22-26-rue-joliette-2019_03597_vdm.pdf": "14/10/2019",  # "14 octobre 2019"
    "27-bd-allemand-13003_2019_03860.pdf": "06/11/2019",  # "6/11/2019"
    "5-rue-pasteur-heuze_13003_ppm_2021_00625.pdf": "25/02/2021",  # "25 février 2021"
    "33-rue-clovis-hugues-13003_2021_01487.pdf": "01/06/2021",  # "1er juin 2021"
    "23-25-rue-du-jet-deau-13003_modif_ps_2021_01728_18-juin-2021_ano.pdf": "18/06/2021",  # 18-juin-2021
    "51-bd-dahdah-13004-2019_04381.pdf": "12/12/2019",  # "12/012/2019"
    "29-rue-nau-13006_2019_01232.pdf": "15/04/2019",  # "15 avril 2019"
    "12-place-nd-du-mont-13006-ms_2021_01990_i.pdf": "08/07/2021",  # "8/07/2021"
    "po_28-rue-des-trois-rois-13006_2020_02117_vdm.pdf": "24/09/2020",  # "24/09"
    "ppm-53-rue-roger-renzo-13008-n2020_02620.pdf": "09/11/2020",  # "9/11/2020"
    "ML-1-TRAVERSE-DE-LA-JULIETTE_2018_03192.pdf": "07/12/2018",  # "7/12/2018"
}


def fix_date_nomdoc(df, verbose=False):
    """Corrige manuellement la date qui devrait être extraite du nom du doc.

    Le nom du doc est le texte du lien sur le site de la ville.

    Parameters
    ----------
    df : DataFrame

    Returns
    -------
    df : DataFrame
        Liste avec date corrigée le cas échéant, sinon date fournie en entrée.
    """
    for url, date_link in FIX_DATE_LINK.items():
        df.loc[df["url"].str.endswith(url), "date_link"] = date_link
    if verbose:
        print("Entrées sans date")
        with pd.option_context("max_colwidth", -1):
            print(df.loc[df["date_link"].isna(), :][["nom_doc", "url"]])
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--liste_csv",
        help="Fichier CSV interim contenant la liste des documents",
        default="data/interim/mrs-arretes-de-peril-{}_fix.csv".format(
            date.today().isoformat()
        ),
    )
    parser.add_argument("--out_dir", help="Base output dir", default="data/interim")
    args = parser.parse_args()
    # fichier brut => fichier corrigé
    fp_in = Path(args.liste_csv).resolve()
    fp_out = Path(args.out_dir) / Path(
        fp_in.stem.rsplit("_", 1)[0] + "_enr" + fp_in.suffix
    )
    # on ouvre le fichier bugué
    df = pd.read_csv(fp_in, dtype="string")
    df.loc[:, "classe"] = df["nom_doc"].apply(predict_doc_class)
    df = extract_date_nomdoc(df)
    df = fix_date_nomdoc(df, verbose=True)
    # on exporte le dataframe corrigé, en gardant le même format que précemment
    # y compris les retours à la ligne du dialecte Excel du CSV Writer :
    # https://docs.python.org/3/library/csv.html#csv.Dialect.lineterminator
    df.to_csv(fp_out, sep=",", index=False, line_terminator="\r\n")
