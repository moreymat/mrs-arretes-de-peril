"""Télécharger les documents à partir d'une liste d'URL.

Si un fichier du même nom a déjà été téléchargé, on s'abstient
de le re-télécharger.
"""

import argparse
import os.path

import pandas as pd
import requests


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('liste_csv',
                        help='Fichier CSV contenant la liste des documents')
    parser.add_argument('out_dir', help='Base output dir')
    args = parser.parse_args()
    #
    dl_dir = os.path.abspath(args.out_dir)
    df = pd.read_csv(args.liste_csv)
    for url in df['url'].values:
        fp = '/'.join(url.split('/')[-2:])
        full_fp = os.path.join(dl_dir, fp)
        os.makedirs(os.path.dirname(full_fp), exist_ok=True)
        if os.path.exists(full_fp):
            # on ne télécharge pas le fichier si on l'a déjà
            continue
        res = requests.get(url)
        with open(full_fp, mode='wb') as f_out:
            f_out.write(res.content)
