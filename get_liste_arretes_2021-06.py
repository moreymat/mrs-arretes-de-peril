"""Télécharger les arrêtés de péril depuis le site de la ville.

2021-06 : les arrêtés sont maintenant classés par arrondissement, puis par rue (par ordre alphabétique)

TODO
- stocker chaque item en HTML et appliquer extract_address(), predict_doc_class() en post-traitement
- sortir directement les classes finales
"""


import argparse
import csv
from datetime import date
import os.path
from pathlib import Path
import re
import unicodedata

import selenium
from selenium import webdriver
from selenium.webdriver.firefox.options import Options


# page centralisant les arrêtés
URL = "http://logement-urbanisme.marseille.fr/am%C3%A9lioration-de-lhabitat/arretes-de-peril"

# chaque arrondissement a un code postal
ART_CP = [("1er arrondissement", "13001")] + [
    ("{}ème arrondissement".format(i), "130{:02}".format(i)) for i in range(2, 17)
]
ART2CP = dict(ART_CP)

# certains items contiennent un code postal: exactement 5 chiffres
# (pas de chiffre juste avant ni juste après)
RE_CP = r"[^\d](?P<cp>\d{5})[^\d]"
MATCH_CP = re.compile(RE_CP)


# selenium helpers
def is_download_finished(temp_folder, fname=None):
    """Check if a file download is finished.

    Parameters
    ----------
    temp_folder : str
        Temporary folder
    fname : str, optional
        File name of the downloaded file.
        If None, any file name will do ('*').

    https://stackoverflow.com/a/53602937
    """
    if fname is None:
        firefox_temp_file = sorted(Path(temp_folder).glob("*.part"))
        chrome_temp_file = sorted(Path(temp_folder).glob("*.crdownload"))
        downloaded_files = sorted(Path(temp_folder).glob("*.*"))
    else:
        firefox_temp_file = sorted(Path(temp_folder).glob(fname + ".part"))
        chrome_temp_file = sorted(Path(temp_folder).glob(fname + ".crdownload"))
        downloaded_files = sorted(Path(temp_folder).glob(fname))
    # do check
    if (
        (len(firefox_temp_file) == 0)
        and (len(chrome_temp_file) == 0)
        and (len(downloaded_files) >= 1)
    ):
        # all good
        return True
    else:
        return False


def _setup_browser(dl_dir, mime_type):
    """Setup Firefox headless browser.

    Parameters
    ----------
    dl_dir : str
        Path to the download dir.
    mime_type : str
        MIME-type that can be automatically downloaded.

    Returns
    -------
    browser : selenium.webdriver.firefox.webdriver.WebDriver
        Firefox browser.
    """
    # Headless Firefox
    options = Options()
    options.add_argument("--headless")
    # prevent download dialog
    profile = webdriver.FirefoxProfile()
    profile.set_preference("browser.download.folderList", 2)  # custom location
    profile.set_preference("browser.download.manager.showWhenStarting", False)
    profile.set_preference("browser.download.dir", dl_dir)
    profile.set_preference("browser.helperApps.neverAsk.saveToDisk", mime_type)
    browser = webdriver.Firefox(firefox_profile=profile, firefox_options=options)
    return browser


# parsing du contenu
def parse_accordion_list(driver, elt):
    """Parse une liste d'accordéons, 1 par arrondissement.

    Parameters
    ----------
    driver : selenium.webdriver.firefox.webdriver.WebDriver
        Driver selenium
    elt : selenium.webdriver.firefox.webelement.FirefoxWebElement
        Element <div> contenant la liste d'accordéons

    Returns
    -------
    docs : List[Tuple[str, str, str, str, str, str]]
        Liste des documents: arrondissement, texte de l'item,
        texte du lien, URL du lien, adresse, code postal.
    """
    docs = []
    # on itère sur des div[@class="card"]
    for e_acc in elt.find_elements_by_xpath('./div[@class="card"]'):
        # div[@class="head-acc"] : bouton arrondissement
        a_head_acc = e_acc.find_element_by_xpath('./div[@class="head-acc"]/a')
        nom_arr = a_head_acc.text
        print(nom_arr)  # suivre la progression du script
        cp_arr = ART2CP[nom_arr]
        # TODO clic a_head_acc ?
        # div[@class="body-acc"]/div[@class="card-body"] : liste de (voie, liste d'adresses)
        # il y a une unique telle liste par arrondissement
        div_body_arr = e_acc.find_elements_by_xpath('./div/div[@class="card-body"]')
        assert len(div_body_arr) == 1
        div_body_arr = div_body_arr[0]
        # on récupère la liste de voies et de listes d'adresses de cette voie
        kids_arr = div_body_arr.find_elements_by_xpath("./*")
        # le 1er et le dernier enfants sont des <p> supplémentaires, autour de paires
        # successives : <p><p><ul><p><ul>...<p><ul><p>
        assert (
            kids_arr[0].tag_name == kids_arr[1].tag_name == kids_arr[-1].tag_name == "p"
        )
        # on peut supprimer ces 1er et dernier <p> qui entourent la vraie liste
        kids_arr.pop(0)
        kids_arr.pop(-1)
        # on itère sur les couples (voie, liste d'adresses)
        for p_voie, ul_voie in zip(kids_arr[:-1], kids_arr[1:]):
            # nom_voie : "Académie (rue de l')"
            nom_voie = p_voie.text
            # itérer sur la liste d'adresses
            for li_adr in ul_voie.find_elements_by_xpath("./li"):
                # adresse : <a>doc1</a> - <a>doc2</a> ...
                li_txt = li_adr.get_attribute("textContent").strip()
                li_txt = unicodedata.normalize("NFKC", li_txt)
                # TODO stocker l'item en HTML (normalisé unicode?) sans l'analyser, et faire l'extraction d'adresse en post-traitement
                # (raw -> interim ?)
                adr_txt = extract_address(li_txt)
                #
                adr_docs = li_adr.find_elements_by_xpath("./a")
                for adr_doc in adr_docs:
                    doc_title = adr_doc.get_attribute("textContent").strip()
                    doc_title = unicodedata.normalize("NFKC", doc_title)
                    doc_url = adr_doc.get_attribute("href")
                    # arrondissement, item, texte du lien, URL du lien, adresse, code postal
                    docs.append((nom_arr, li_txt, doc_title, doc_url, adr_txt, cp_arr))
    return docs


def extract_address(li_txt):
    """Extrait l'adresse à partir du texte d'un list item"""
    # extraction de l'adresse, parfois un autre séparateur est utilisé
    # FIXME correctif cracra pour entrée cracra
    if (
        li_txt
        == "Abrogation d'arrêté portant sur l'installation d'un périmètre de sécurité sur un passage privé - Parcelle N°207834 C0151"
    ):
        adr_txt = "rue d'Endoume"
    else:
        adr_txt = li_txt
        if ": " in adr_txt:
            adr_txt = adr_txt.split(": ")[0]
        if "   " in adr_txt:
            adr_txt = adr_txt.split("   ")[0]
        if "  " in adr_txt:
            adr_txt = adr_txt.split("  ")[0]
        if " - Arr" in adr_txt:
            adr_txt = adr_txt.split(" - ")[0]
        if " - Abr" in adr_txt:
            adr_txt = adr_txt.split(" - ")[0]
        if " Arrêté" in adr_txt:
            adr_txt = adr_txt.split(" Arrêté")[0]
    adr_txt = adr_txt.strip()
    if adr_txt.endswith(" -"):
        # nettoyage cracra
        adr_txt = adr_txt[:-2]
    return adr_txt


def parse_arretes(
    driver: selenium.webdriver.remote.webdriver.WebDriver, url: str, outdir: str
):
    """Extraire les descriptions et liens des arrêtés depuis la page web.

    Parameters
    ----------
    driver : selenium.webdriver
        Driver selenium
    url : string
        URL de la page listant les arrêtés de péril
    outdir : string
        Chemin vers le dossier où seront stockés les arrêtés téléchargés.
    """
    driver.get(url)
    # on vérifie le titre de la page
    assert driver.title == "Arrêtés de péril | Ville de Marseille"
    # la page contient une (unique) liste d'accordéons
    div_accordions_wrapper = driver.find_elements_by_xpath(
        '//div[@id="dexp-accordions-wrapper"]'
    )
    assert len(div_accordions_wrapper) == 1
    div_accordions_wrapper = div_accordions_wrapper[0]
    # on extrait les documents des 16 accordéons
    docs = parse_accordion_list(driver, div_accordions_wrapper)
    # 2021-06 la classe de documents n'est plus fournie, on garde le champ pour rétro-compatibilité
    # mais on prédira sa valeur après (voir enrich_liste_arretes)
    res = [("?", x[0], x[1], x[2], x[3], x[4], x[5]) for x in docs]
    return res


def dump_doc_list(docs, fn_out):
    """Exporter la liste des documents dans un fichier CSV.

    Parameters
    ----------
    docs: List[(str, str, str, str)]
        Documents
    fn_out : string
        Chemin du fichier CSV de sortie
    """
    # on écrit la liste des documents dans un fichier CSV
    colnames = [
        "classe",
        "arrondissement",
        "item",
        "nom_doc",
        "url",
        "adresse",
        "code_postal",
    ]
    with open(fn_out, mode="w", newline="", encoding="utf-8") as f_out:
        csv_out = csv.writer(f_out)
        csv_out.writerow(colnames)
        for row in docs:
            csv_out.writerow(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out_dir", help="Base output dir", default="data/raw")
    args = parser.parse_args()
    # dossier de base pour stocker les documents téléchargés
    dl_dir = os.path.abspath(args.out_dir)
    os.makedirs(dl_dir, exist_ok=True)
    # les arrêtés sont des PDFs
    driver = _setup_browser(dl_dir, "application/pdf")
    #
    docs = parse_arretes(driver, URL, dl_dir)
    # on ajoute la date du jour
    today = date.today().isoformat()
    # on écrit la liste dans un fichier CSV
    fn_out = f"mrs-arretes-de-peril-{today}.csv"
    fp_out = os.path.join(dl_dir, fn_out)
    dump_doc_list(docs, fp_out)
