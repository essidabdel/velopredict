"""Worker de process isolé pour la régression linéaire.

Pourquoi : entraîner scikit-learn `LinearRegression` puis LightGBM dans le
même process Python provoque un crash natif reproductible (violation
d'accès mémoire dans `LGBM_DatasetSetField`) sur cette machine Windows —
conflit probable entre les runtimes OpenMP/BLAS natifs de ces deux
bibliothèques compilées (`KMP_DUPLICATE_LIB_OK=TRUE` n'a pas suffi à le
résoudre). L'isolation par sous-process est le contournement le plus
simple et fiable : chaque bibliothèque native vit dans son propre
process, donc plus de conflit possible. Inoffensif sur une machine qui
n'a pas ce problème. Invoqué par ml/train.py, pas destiné à un usage
direct.
"""

from __future__ import annotations

import argparse

import joblib
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import FEATURE_COLUMNS


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-path", required=True, help="Parquet contenant features + cible")
    parser.add_argument("--target", required=True)
    parser.add_argument("--output-path", required=True)
    args = parser.parse_args()

    train = pd.read_parquet(args.train_path)
    model = make_pipeline(StandardScaler(), LinearRegression())
    model.fit(train[FEATURE_COLUMNS], train[args.target])
    joblib.dump(model, args.output_path)


if __name__ == "__main__":
    main()
