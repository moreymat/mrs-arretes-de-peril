"""Enrichit la liste des arrêtés avec des informations extraites de la page du site.

TODO
- [ ] implanter (dans un autre module, en aval) une variante plus fiable de catégorisation de documents, qui utilise le texte de l'arrêté
"""


import argparse
from datetime import date
from pathlib import Path
import re

import pandas as pd

# arrêté de main-levée partielle
RE_MLP = r"mai[ln][- ]?l[ée]v[ée]e partiel(le)?"
M_MLP = re.compile(RE_MLP, re.IGNORECASE)
# arrêté de main-levée
RE_ML = r"mai[ln][- ]?l[ée]v[ée]e"
M_ML = re.compile(RE_ML, re.IGNORECASE)
# abrogation
RE_ABRO = r"abrogati"
M_ABRO = re.compile(RE_ABRO, re.IGNORECASE)
# évacuation
RE_EVAC = r"[ée]vacuation"
M_EVAC = re.compile(RE_EVAC, re.IGNORECASE)
# réintégration partielle
RE_REINTEG_P = r"r[ée]int[ée]gration partielle"
M_REINTEG_P = re.compile(RE_REINTEG_P, re.IGNORECASE)
# réintégration
RE_REINTEG = r"r[ée]int[ée]gration"
M_REINTEG = re.compile(RE_REINTEG, re.IGNORECASE)
# arrêté modificatif (de?)
RE_MODIF = r"modificati"
M_MODIF = re.compile(RE_MODIF, re.IGNORECASE)
# arrêté de péril ordinaire
RE_PERIL_ORD = r"p[ée]?ril ordinaire"
M_PERIL_ORD = re.compile(RE_PERIL_ORD, re.IGNORECASE)
# arrêté de péril grave et imminent
RE_PERIL_GI = r"p[ée]?ril grave (et )?im[m]?in[n]?ent"
M_PERIL_GI = re.compile(RE_PERIL_GI, re.IGNORECASE)
# arrêté de péril imminent
RE_PERIL_IMM = r"p[ée]?ril imminent"
M_PERIL_IMM = re.compile(RE_PERIL_IMM, re.IGNORECASE)
# arrêté de péril
RE_PERIL = r"p[ée]?ril"
M_PERIL = re.compile(RE_PERIL, re.IGNORECASE)
#
RE_PERIM = r"périmètre[s]? de (sécurité|protection)"
M_PERIM = re.compile(RE_PERIM, re.IGNORECASE)
#
RE_INTER_OCCUP = r"(inte[r]?diction.*)?d'occup"
M_INTER_OCCUP = re.compile(RE_INTER_OCCUP, re.IGNORECASE)
#
RE_MSU = r"mi[s]?e en séc(ur|ru)it[t]?é urgente"
M_MSU = re.compile(RE_MSU, re.IGNORECASE)
#
RE_MISE_SECU = r"mi[s]?e en séc(ur|ru)it[t]?é"
M_MISE_SECU = re.compile(RE_MISE_SECU, re.IGNORECASE)
# restent :
# - [ ] arrêtés à qualifier "arrêté du" ;
# - [ ] "astreinte administrative"


def predict_doc_class(doc_text):
    """Prédit la classe d'un document, parmi les 8 possibles.

    Classes :
    * Arrêtés de péril ordinaire,
    * Arrêtés de péril grave,
    * Arrêtés de péril imminent,
    * Arrêtés de péril grave et imminent,
    * Arrêtés de mainlevée,
    * Arrêtés de mainlevée partielle,
    * Arrêtés modificatifs,
    * Abrogations,
    * Arrêtés d'évacuation,
    * Arrêtés de réintégration partielle,
    * Arrêtés de réintégration,
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
    if M_MLP.search(doc_text):
        doc_class = "Arrêtés de mainlevée partielle"
    elif M_ML.search(doc_text):
        doc_class = "Arrêtés de mainlevée"
    elif M_ABRO.search(doc_text):
        doc_class = "Abrogations"
    elif M_REINTEG_P.search(doc_text):
        doc_class = "Arrêtés de réintégration partielle"
    elif M_REINTEG.search(doc_text):
        doc_class = "Arrêtés de réintégration"
    elif M_EVAC.search(doc_text):
        doc_class = "Arrêtés d'évacuation"
    elif M_MODIF.search(doc_text):
        # TODO préciser modificatif de quoi
        doc_class = "Arrêtés modificatifs"
    elif M_PERIL_ORD.search(doc_text):
        doc_class = "Arrêtés de péril ordinaire"
    elif M_PERIL_IMM.search(doc_text):
        doc_class = "Arrêtés de péril imminent"
    elif M_PERIL_GI.search(doc_text):
        doc_class = "Arrêtés de péril grave et imminent"
    # elif M_PERIL.search(doc_text):
    # heuristique : "péril" (sans plus de précision) est ici "péril imminent"
    # TODO vérifier si cette heuristique tient
    # doc_class = "Arrêtés de péril imminent"
    elif "insécurité" in doc_text:
        doc_class = "Arrêtés d'insécurité imminente des équipements communs"
    elif M_INTER_OCCUP.search(doc_text):
        doc_class = "Arrêtés d'interdiction d'occuper"
    elif "police générale" in doc_text:
        doc_class = "Arrêtés de police générale"
    elif "évacuation" in doc_text or "réintégration" in doc_text:
        doc_class = "Arrêtés d'évacuation et de réintégration"
    elif "diagnostic d'ouvrages" in doc_text:
        doc_class = "Diagnostics d'ouvrages"
    elif M_PERIM.search(doc_text) is not None:
        doc_class = "Arrêtés de périmètres de sécurité sur voie publique"
    elif "déconstruction" in doc_text:
        doc_class = "Arrêtés de déconstruction"
    # évolution réglementaire 2021
    elif M_MSU.search(doc_text):
        doc_class = "Arrêtés de mise en sécurité urgente"
    elif M_MISE_SECU.search(doc_text):
        doc_class = "Arrêtés de mise en sécurité"
    # classe inconnue => objectif : résorber le nombre d'occurrences
    else:
        doc_class = "?"
    return doc_class


# péril simple
RE_PS = r"[/_-]ps[/_-]"
M_PS = re.compile(RE_PS, re.IGNORECASE)
# péril ordinaire
RE_PO = r"[/_-]po[/_-]"
M_PO = re.compile(RE_PO, re.IGNORECASE)
# péril imminent
RE_PI = r"[/_-]pi[/_-]"
M_PI = re.compile(RE_PI, re.IGNORECASE)
# péril grave et imminent
RE_PGI = r"[/_-]pgi[/_-]"
M_PGI = re.compile(RE_PGI, re.IGNORECASE)


def guess_doc_class(s_row):
    """Devine la classe d'un document.

    Actuellement à partir de son URL.

    Parameters
    ----------
    s_row : Series
        Ligne de la liste des documents.

    Returns
    -------
    doc_class : string
        Classe du document
    """
    if M_PGI.search(s_row["url"]):
        # péril grave et imminent
        doc_class = "Arrêtés de péril grave et imminent"
    elif M_PI.search(s_row["url"]):
        # péril imminent
        doc_class = "Arrêtés de péril imminent"
    elif M_PO.search(s_row["url"]):
        # péril ordinaire
        doc_class = "Arrêtés de péril ordinaire"
    elif M_PS.search(s_row["url"]):
        # péril simple
        doc_class = "Arrêtés de péril simple"
    elif "mlpi" in s_row["url"]:
        # mainlevée de péril imminent
        # TODO préciser le péril imminent dans la classe ?
        doc_class = "Arrêtés de mainlevée"
    elif "pni" in s_row["url"]:
        # péril non imminent
        # FIXME ? garder une classe spécifique ?
        doc_class = "Arrêtés de péril non imminent"
    elif "msu" in s_row["url"]:
        # mise en sécurité urgente (terminologie 2021)
        # FIXME ? définir une classe plus spécifique ?
        doc_class = "Arrêtés de mise en sécurité urgente"
    elif "ml" in s_row["url"]:
        # main-levée
        doc_class = "Arrêtés de mainlevée"
    elif "occup" in s_row["url"]:
        # interdiction d'occuper
        doc_class = "Arrêtés d'interdiction d'occuper"
    elif "police" in s_row["url"]:
        # police générale
        doc_class = "Arrêtés de police générale"
    elif "perimetre" in s_row["url"]:
        # périmètre de sécurité
        doc_class = "Arrêtés de périmètres de sécurité sur voie publique"
    else:
        # 2021-07-26 : 199 occurrences "?"
        # heuristique => "péril grave et imminent"
        # doc_class = "?"
        doc_class = "Arrêtés de péril grave et imminent"
    return doc_class


FIX_URL_DOC_CLASS = {
    "10a-rue-baussenque-13002_2019_03982.pdf": "Arrêtés de péril grave et imminent",
    "33-rue-danton-13003_2021_00599.pdf": "Arrêtés de mise en sécurité urgente",
    "5-bis-impasse-de-l-ouest-13003_2019_01497.pdf": "Arrêtés de péril grave et imminent",
    "4-rue-eugene-pottier-1-rue-hoche-13003_2021_00752.pdf": "Arrêtés de mise en sécurité",
    "154-156-avenue-roger-salengro-13003_2021_00898.pdf": "Arrêtés de mise en sécurité",
    "197_BD_DE_LA_LIBERATION_ANGLE_ESPERANDIEU-130042019_00619.pdf": "Arrêtés de péril grave et imminent",
    "33-avenue-de-montolivet-13004_2021_00378.pdf": "Arrêtés de mise en sécurité",
    "102-bd-baille_po_2020_02311.pdf": "Arrêtés de péril ordinaire",
    "132-boulevard-baille-13005_2019_01326.pdf": "Arrêtés de péril grave et imminent",
    "6-BD-LOUIS-FRANGIN-13005_2018_03428.pdf": "Arrêtés de péril imminent",
    "59-place-jean-jaures_13006_arrete_astreinte_2021_01383_22-mai-2021.pdf": "Arrêtés d'astreinte administrative",
    "40-rue-de-l-olivier-13005_2019_00047.pdf": "Arrêtés de péril imminent",
    "37-rue-fernand-pauriol-13005_2019_03910.pdf": "Arrêtés de péril grave et imminent",
    "arrete-du-maire-7-rue-du-portail-13005.pdf": "Arrêtés de dérogation à la prorogation des délais",
    "21_rue_du_portail-13005_2019_01152.pdf": "Arrêtés de péril grave et imminent",
    "15-place-castellane-13006_ppm_2021_01730_17-juin-2021.pdf": "Arrêtés d'interdiction d'occuper",
    "18-RUE-BERLIOZ-13006_2019_00659.pdf": "Arrêtés de péril grave et imminent",
    "51-rue-fongate-13006_2019_03856.pdf": "Arrêtés d'interdiction d'occuper",
    "55-rue-fongate-13006_2019_03857.pdf": "Arrêtés d'interdiction d'occuper",
    "abro_ppm_2020_00054_vdm.pdf": "Abrogations",
    "88-cours-gouffe-13006_2018_03019.pdf": "Arrêtés de péril imminent",
    "ppm_19-rue-d-italie-13006_2019_04289_vdm.pdf": "Arrêtés de péril grave et imminent",
    "19-rue-italie-13006_2021_00885.pdf": "Arrêtés modificatifs",  # de péril simple
    "81-RUE-D-ITALIE-13006_2019_00545.pdf": "Arrêtés de péril grave et imminent",
    "59-place-jean-jaures-13006_2019_02468.pdf": "Arrêtés de péril grave et imminent",
    "61-place-jean-jaures-13006_2019_02469.pdf": "Arrêtés de péril grave et imminent",
    "31-rue-nau-13006_2019_02300.pdf": "Arrêtés de péril grave et imminent",
    "po_31-rue-nau-13006_2020_02829_vdm.pdf": "Arrêtés de péril ordinaire",
    "29-rue-nau-13006_2019_01232.pdf": "Arrêtés de péril grave et imminent",
    "29-rue-nau-13006_2020-12-01_po-2020_02835.pdf": "Arrêtés de péril ordinaire",
    "ppm_14-boulevard-salvator-13006_2019_04291_vdm.pdf": "Arrêtés d'interdiction d'occuper",
    "80-RUE-PERRIN-SOLLIERS-13006_2019_00384.pdf": "Arrêtés de péril grave et imminent",
    "41-rue-d-endoume-13007_2018_03313.pdf": "Arrêtés de péril imminent",
    "26-rue-sainte-13001_mes_ndeg2021_00186_vdm_du_19-01-21.pdf": "Arrêtés de mise en sécurité",
    "301-avenue-de-la-capelette-13010_2019_02297.pdf": "Arrêtés de péril grave et imminent",
    "ordonnance_37-boulevard-gilly-13010.pdf": "Ordonnances du Tribunal Administratif",
    "ML-1-TRAVERSE-DE-LA-JULIETTE_2018_03192.pdf": "Arrêtés de mainlevée",  # de péril imminent
    "19-24-DOMAINE-VENTRE-13001_2019_00537.pdf": "Arrêtés de péril grave et imminent",
    "po_2020_01674_-4-ruepytheas-13001-vdm.pdf": "Arrêtés de péril ordinaire",
    "4-rue-pytheas-arrete_pi_2018_02930-final.pdf": "Arrêtés de péril imminent",
    "pgi_14-cours-saint-louis_2-rue-de-rome_2-rue-rouget-de-l-isle_2019_04210_vdm.pdf": "Arrêtés de péril grave et imminent",
    "24-rue-de-la-bibliotheque-13001_po_2020_02957_10-12-20.pdf": "Arrêtés de péril ordinaire",
    "43-rue-curiol-13001_2019_01315_vdm.pdf": "Arrêtés de péril grave et imminent",
    "45-rue-curiol-13001_2019_01314.pdf": "Arrêtés de péril grave et imminent",
    "ps_29-rue-des-dominicaines-13001_2019_03108_vdm.pdf": "Arrêtés de péril simple",
    "108-avenue-des-chartreux_2021_00263.pdf": "Arrêtés de mise en sécurité urgente",
    "103-avenue-roger-salengro-13003-2020_02856.pdf": "Arrêtés de péril imminent",
    "42-rue-de-bruys-13005_2018_03303.pdf": "Arrêtés de péril imminent",
}


def fix_doc_class(df, verbose=False):
    """Corrige manuellement la classe d'un ensemble de documents.

    Parameters
    ----------
    df : pd.DataFrame
        La liste de documents.

    Returns
    -------
    df : DataFrame
        Liste avec date corrigée le cas échéant, sinon date fournie en entrée.
    """
    for url, doc_class in FIX_URL_DOC_CLASS.items():
        df.loc[df["url"].str.endswith(url), "classe"] = doc_class
    if verbose:
        print("Entrées sans classe")
        with pd.option_context("max_colwidth", -1):
            print(df.loc[df["classe"].isna(), :][["nom_doc", "url"]])
    return df


# date

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
    "15-rue-du-jet-d-eau-13003_pgi_2019_02875.pdf": "14/08/2019",  # "14/08/20219"
    "7-rue-des-cartiers-13002_ppm-2021_00034.pdf": "07/01/2021",  # "07/11/2021"
    "ml-partielle_pgi_4-rue-beaussenque-13002_2019_02551.pdf": "22/07/2019",  # "22/07/21019"
    "42-rue-de-bruys-13005_2018_03303.pdf": "12/12/2018",  # "18/12/2020"
    "73-chemin-de-st-henri-13016_2021_01956.pdf": "17/07/2021",  #
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
    df.loc[df["classe"] == "?", "classe"] = df.loc[df["classe"] == "?", :].apply(
        guess_doc_class, axis=1
    )
    df = fix_doc_class(df, verbose=True)
    #
    df = extract_date_nomdoc(df)
    df = fix_date_nomdoc(df, verbose=True)
    # on exporte le dataframe corrigé, en gardant le même format que précemment
    # y compris les retours à la ligne du dialecte Excel du CSV Writer :
    # https://docs.python.org/3/library/csv.html#csv.Dialect.lineterminator
    df.to_csv(fp_out, sep=",", index=False, line_terminator="\r\n")
