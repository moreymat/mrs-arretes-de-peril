"""Télécharger les documents à partir d'une liste d'URL.

Si un fichier du même nom a déjà été téléchargé, on s'abstient
de le re-télécharger.
"""

import argparse
from pathlib import Path
import os.path

import pandas as pd
import requests


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "liste_csv", help="Fichier CSV contenant la liste des documents"
    )
    parser.add_argument("out_dir", help="Base output dir")
    args = parser.parse_args()
    #
    dl_dir = os.path.abspath(args.out_dir)
    # fichier interim => fichier traité
    fp_int = Path(args.liste_csv).resolve()
    fp_pro = fp_int.parents[1] / "processed" / fp_int.name
    #
    df = pd.read_csv(fp_int, dtype="string")
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
    df.to_csv(fp_pro, sep=",", index=False, line_terminator="\r\n")
