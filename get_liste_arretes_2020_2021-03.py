"""Télécharger les arrêtés de péril depuis le site de la ville"""


import argparse
import csv
from datetime import date
import os.path
from pathlib import Path
import re
import unicodedata

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


def parse_plain_list(driver, elt):
    """Parse une liste d'items

    Parameters
    ----------
    driver : selenium.webdriver.firefox.webdriver.WebDriver
        Driver selenium
    elt : FirefoxWebElement
        Element contenant la liste d'accordéons
    outdir : string
        Dossier de stockage des documents

    Returns
    -------
    docs : List[(str, str, str, str)]
        Liste des documents, décrits par l'adresse, le texte
        complet de l'item (dont adresse), le texte du lien et
        l'URL du lien.
    """
    docs = []
    for e_it in elt.find_elements_by_xpath("./li"):
        e_text = e_it.get_attribute("textContent").strip()
        e_text = unicodedata.normalize("NFKC", e_text)
        # extraction de l'adresse
        e_addr = e_text
        # l'adresse s'arrête dès qu'on rencontre
        # un de ces termes
        rlimits = [
            "Arrêté",
            "Arrrété",
            "arreté",
            "Arrété",
            "Arrête",
            "Main Levée",
            "Main levée",
            "Main-Levée",
            "main levée",
            "Mainlevée",
            "Modification",
            "Abrogation",
            "abrogé",
            "remplacé",
            "Interdiction",
        ]
        for rlimit in rlimits:
            if rlimit in e_addr:
                e_addr = e_addr.split(rlimit)[0]
        # on récupère le code postal si présent
        m_cp = MATCH_CP.search(e_addr)
        if m_cp is not None:
            e_cp = m_cp.group("cp")
            # et on le supprime du texte de l'adresse
            # (redondant maintenant qu'on a un champ dédié)
            e_addr = re.sub(RE_CP, "", e_addr)
        else:
            e_cp = ""
        # nettoyage des caractères avant/après
        e_addr = e_addr.lstrip().rstrip(" -:/+(")
        # item, texte du lien, URL du lien, adresse, code postal
        docs.extend(
            [
                (
                    e_text,
                    x.get_attribute("textContent"),
                    x.get_attribute("href"),
                    e_addr,
                    e_cp,
                )
                for x in e_it.find_elements_by_xpath("./a")
            ]
        )
    return docs


def parse_accordion_list(driver, elt):
    """Parse une liste d'accordéons

    Parameters
    ----------
    driver : selenium.webdriver.firefox.webdriver.WebDriver
        Driver selenium
    elt : FirefoxWebElement
        Element contenant la liste d'accordéons
    outdir : string
        Dossier de stockage des documents

    Returns
    -------
    docs : List[]
        Liste des documents: arrondissement, texte de l'item,
        texte du lien, URL du lien.
    """
    docs = []
    for e_acc in elt.find_elements_by_xpath("./div"):
        # e_key = e_acc.find_element_by_xpath('./strong/div/h4/a').text  # 2020-02
        # 2021-03
        e_key = e_acc.find_element_by_xpath('./div[@class="head-acc"]/a').text
        elts_ul = e_acc.find_elements_by_xpath("./div/div/ul")
        assert len(elts_ul) == 1
        elt_ul = elts_ul[0]
        e_docs = parse_plain_list(driver, elt_ul)
        # on définit le code postal à partir du numéro d'arrondissement
        elt_cp = ART2CP[e_key]
        # on vérifie qu'il n'y a pas de conflit entre ce code postal
        # et celui éventuellement extrait du texte de l'item (rare mais
        # possible dans les accordéons)
        try:
            assert all(elt_cp == x[4] for x in e_docs if x[4])
        except AssertionError:
            print(elt_cp)
            print([x[4] for x in e_docs])
            raise
        # à ce point, elt_cp == x[1] si ce dernier existe
        # donc on peut écraser x[1] par elt_cp et supprimer
        # l'arrondissement
        docs.extend([(e_key, x[0], x[1], x[2], x[3], elt_cp) for x in e_docs])
    return docs


def parse_arretes(driver, url, outdir):
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
    # la page est divisée en 8 sections (au 2020-02-26) correspondant chacune
    # à une classe de documents:
    # * Arrêtés de péril imminent, de Main Levée et de Réintégration partielle,
    # * Arrêtés d'insécurité imminente des équipements communs,
    # * Arrêtés d'interdiction d'occuper,
    # * Arrêtés de police générale,
    # * Arrêtés d'évacuation et de réintégration,
    # * Diagnostics d'ouvrages,
    # * Arrêtés de périmètres de sécurité sur voie publique,
    # * Arrêtés de déconstruction
    # les sections sont dans un <div class="field-item even">,
    # chaque section a un titre h4
    cont_div = driver.find_elements_by_xpath('//div[@class="field-items"]/div')
    assert len(cont_div) == 1
    cont_div = cont_div[0]
    #
    res = []
    for section in cont_div.find_elements_by_xpath("./h4"):
        # chaque section a un titre h4
        doc_class = section.text.replace("Consultez les derniers ", "").replace(
            " par arrondissement (ordre chronologique)", ""
        )
        # on affiche la section pour suivre la progression du script
        print(doc_class)
        # chaque section a une liste de documents, directement ou dans
        # une liste d'accordéons (un par arrondissement)
        next_elt = section.find_element_by_xpath("./following-sibling::*[1]")
        if next_elt.tag_name == "ul":
            # * liste directe: <ul>
            docs = parse_plain_list(driver, next_elt)
            # on ne connaît pas l'arrondissement
            res.extend([(doc_class, "", x[0], x[1], x[2], x[3], x[4]) for x in docs])
        elif next_elt.tag_name == "p":
            # * accordéon: <p><div[id="dexp-accordions-wrapper--...")]>"
            elt_acc = next_elt.find_element_by_xpath("./following-sibling::div[1]")
            docs = parse_accordion_list(driver, elt_acc)
            # classe, arrondissement, adresse, code postal, item,
            # texte du lien, URL du lien
            res.extend([(doc_class, x[0], x[1], x[2], x[3], x[4], x[5]) for x in docs])
        else:
            # * structure inattendue
            e_html = next_elt.tag_name + " " + next_elt.get_attribute("innerHTML")
            raise ValueError("Structure de page inattendue\n{}".format(e_html))
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
    parser.add_argument("out_dir", help="Base output dir")
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
