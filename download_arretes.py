"""Télécharger les documents à partir d'une liste d'URL.

Si un fichier du même nom a déjà été téléchargé, on s'abstient
de le re-télécharger.
"""

import argparse
from datetime import date
from pathlib import Path
import os.path

import pandas as pd
import requests


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--liste_csv",
        help="Fichier CSV interim contenant la liste des documents",
        default="data/interim/mrs-arretes-de-peril-{}_enr.csv".format(
            date.today().isoformat()
        ),
    )
    parser.add_argument(
        "--out_dir",
        help="Dossier de sortie pour le CSV traité",
        default="data/processed",
    )
    parser.add_argument(
        "--doc_dir", help="Dossier de stockage des documents", default="data/arretes"
    )
    args = parser.parse_args()
    #
    dl_dir = os.path.abspath(args.doc_dir)
    # fichier interim => fichier traité
    fp_in = Path(args.liste_csv).resolve()
    fp_out = Path(args.out_dir) / Path(fp_in.name.rsplit("_", 1)[0] + fp_in.suffix)
    #
    df = pd.read_csv(fp_in, dtype="string")
    #
    idc_urls_404 = []  # index des URLs qui ne répondent pas
    for index, url in df["url"].dropna().items():
        fp = "/".join(url.split("/")[-2:])
        full_fp = os.path.join(dl_dir, fp)
        os.makedirs(os.path.dirname(full_fp), exist_ok=True)
        if os.path.exists(full_fp):
            # on ne télécharge pas le fichier si on l'a déjà
            continue
        print(url)  # TODO progress bar?
        res = requests.get(url)
        try:
            res.raise_for_status()
        except:
            # FIXME stocker l'info de fichier manquant?
            print(f"ERR: Impossible d'atteindre {url}")
            idc_urls_404.append(index)
            continue
        else:
            with open(full_fp, mode="wb") as f_out:
                f_out.write(res.content)
    df.loc[idc_urls_404, "url"] = ""
    # on exporte le dataframe corrigé, en gardant le même format que précemment
    # y compris les retours à la ligne du dialecte Excel du CSV Writer :
    # https://docs.python.org/3/library/csv.html#csv.Dialect.lineterminator
    df.to_csv(fp_out, sep=",", index=False, line_terminator="\r\n")
