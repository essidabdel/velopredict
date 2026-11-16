# Résultats — modèle de prédiction VéloPredict

Prédiction du nombre total de vélos disponibles (mécaniques + électriques)
par station, à t+30 et t+60 minutes.

**Versions du modèle** : ce rapport décrit le modèle **réentraîné le
16 novembre 2026** sur toute la fenêtre disponible (5 octobre → 16 novembre,
historique importé + collecte en direct). Les chapitres 3, 5, 6, 7, 9 et 10
ont été recalculés sur ce modèle. Les chapitres 11 et 12 (second jeu de test
du 2-3 novembre, évaluation sur données live) et le chapitre 13 de contexte
**n'ont pas été recalculés** : leurs chiffres datent de la première version,
`model-v1` (tag git ; copie locale dans `ml/models/model-v1/`, hors git).

## 1. Vérification : cibles calculées par horodatage réel, pas par shift

Le calcul initial des lags/cibles utilisait `groupby().shift()` — un
décalage **de position** dans la série, correct uniquement parce que la
grille est construite pour être parfaitement régulière (une ligne par
station toutes les 15 min). C'était une hypothèse implicite, jamais
vérifiée : un trou dans la grille (ou un filtrage fait avant ce calcul)
aurait silencieusement donné des cibles fausses.

**Corrigé** : `ml/features.py` calcule désormais chaque lag/cible par une
**jointure explicite sur l'horodatage réel** (`station_id` + `ts ± offset`),
dans `_join_on_timestamp` :

```python
def _join_on_timestamp(df: pd.DataFrame, offset_minutes: int, column_name: str) -> pd.DataFrame:
    """Jointure explicite sur l'horodatage réel ts + offset (station_id,
    horodatage exact), pas un décalage de lignes."""
    lookup = df[["station_id", "ts", "bikes"]].rename(
        columns={"ts": "_lookup_ts", "bikes": column_name}
    )
    df = df.copy()
    df["_lookup_ts"] = df["ts"] + pd.Timedelta(minutes=offset_minutes)
    df = df.merge(lookup, on=["station_id", "_lookup_ts"], how="left")
    return df.drop(columns=["_lookup_ts"])
```

`bikes_t_plus_30` cherche exactement la ligne à `ts + 30min` pour la même
station ; si elle n'existe pas (trou, station filtrée inactive...), le
résultat est `NaN` (ligne ensuite éliminée par `dropna`), jamais une
valeur d'une ligne voisine prise par erreur.

**Preuve par le test** (`tests/ml/test_features.py`) : une grille avec un
trou volontaire (pas de relevé à 00:30) confirme que la cible à t+30 de
la ligne 00:00 est bien `NaN`, là où un `shift(-2)` positionnel aurait
silencieusement renvoyé la valeur de la ligne suivante (00:45). Ce test
aurait échoué avec l'ancien code.

## 2. Stations inactives exclues

`ml/features.py::filter_active_stations` retire, avant le calcul des
lags/cibles, tout relevé où `is_renting = 0` ou où `last_reported` est
plus vieux que 2h par rapport à l'horodatage du relevé (station qui ne
répond plus au flux GBFS). Appliqué **avant** les jointures temporelles :
un relevé inactif ne sert ni de feature (on ne prédit pas depuis un état
fermé), ni de cible (on ne prédit pas vers un état fermé — son absence
fait naturellement échouer la jointure chez un voisin actif, donnant
`NaN` puis exclusion).

Effet mesuré sur la fenêtre d'entraînement : **3 782 472 → 3 652 511
lignes** (-3.4%, ~130 000 relevés de stations fermées/hors service
retirés).

## 3. Données et découpage temporel — dates précises

- **Fenêtre** : 2026-10-05 → 2026-11-16, limitée aux jours fiables
  (`v_training_eligible_status`, voir `ingestion/backfill.py`) — elle inclut
  désormais la collecte en direct accumulée depuis le lancement.
- **3 805 430 lignes** de features (après filtrage des stations
  inactives).
- **TRAIN** : 3 043 367 lignes, **du 2026-10-05 22:32 UTC au 2026-10-28
  12:47 UTC**.
- **TEST** : 762 063 lignes, **du 2026-10-28 13:02 UTC au 2026-11-15
  22:17 UTC** (~18 jours, jamais vus à l'entraînement).
- Découpage strictement temporel (jamais aléatoire) : le test est
  entièrement postérieur au train, aucune ligne au même horodatage des
  deux côtés (vérifié, voir `tests/ml/test_train.py`).

## 4. Variables

`heure`, `jour_semaine`, `is_weekend`, `is_public_holiday`,
`is_school_holiday`, `temperature_c`, `precipitation_mm`,
`wind_speed_kmh`, `bikes_t`, `bikes_t_minus_15`, `bikes_t_minus_30`,
`bikes_t_minus_60`, `docks_t`, `capacity`, `lat`, `lon`.

Cible = nombre total de vélos (mécaniques + électriques combinés) ; le
détail par type n'est pas modélisé séparément dans cette version.

## 5. Résultats — MAE / RMSE par horizon (tableau complet, 5 modèles)

| Horizon | Modèle | MAE | RMSE |
|---|---|---|---|
| t+30min | persistance | 1.437 | 3.128 |
| t+30min | moyenne historique | 5.523 | 7.814 |
| t+30min | régression linéaire | 1.575 | 2.906 |
| t+30min | LightGBM (niveau) | 1.420 | 2.623 |
| t+30min | **LightGBM (variation)** | **1.410** | **2.618** |
| t+60min | persistance | 2.059 | 3.769 |
| t+60min | moyenne historique | 5.526 | 7.813 |
| t+60min | régression linéaire | 2.135 | 3.589 |
| t+60min | LightGBM (niveau) | 2.006 | 3.430 |
| t+60min | **LightGBM (variation)** | **2.003** | **3.440** |

*(fichier complet : `ml/reports/metriques.csv`)*

**LightGBM (niveau) bat la persistance sur les deux horizons** : MAE
-1,2 % à t+30 (1.420 vs 1.437) et -2,6 % à t+60 (2.006 vs 2.059) ; RMSE
-16,1 % à t+30 (2.623 vs 3.128) et -9,0 % à t+60. L'écart en MAE est faible
parce que, sur ~40 % des lignes, la disponibilité ne bouge pas du tout (la
persistance y est parfaite) ; le chapitre 7 isole les lignes qui changent
réellement. Le RMSE, qui pénalise les grosses erreurs, montre que le modèle
évite surtout les gros écarts.

## 6. LightGBM niveau vs LightGBM variation (delta)

Variante entraînée à prédire `y(t+h) - bikes_t` plutôt que le niveau
absolu, puis reconstruite en niveau (`bikes_t + delta_prédit`) pour rester
comparable (`ml/train.py::DeltaLightGBM`). Résultat : **légèrement
meilleure** que la version niveau sur les deux horizons (MAE 1.410 vs 1.420 à t+30 ; 2.003 vs 2.006 à t+60) — un gain marginal (≤ 0,7 %), pas
une rupture. Logique : les deux versions ont accès à `bikes_t` comme
feature, donc apprennent en pratique une fonction très proche ; forcer
explicitement la cible à être une variation aide un peu à régulariser
mais ne change pas fondamentalement ce que le modèle peut apprendre ici.
Le modèle **actuellement servi par l'API reste la version niveau**
(`lightgbm_{30,60}.joblib`) ; la variante delta est documentée pour
comparaison, pas déployée (gain trop marginal pour justifier la
complexité supplémentaire côté inférence).

## 7. MAE restreinte aux lignes où la disponibilité change réellement

La MAE globale est flattée par les lignes où rien ne bouge (persistance y
est mécaniquement parfaite). En ne gardant que les lignes où
`bikes_t_plus_h != bikes_t` (**60,2 %** des lignes de test à t+30,
**72,3 %** à t+60 — l'écart entre les deux montre que plus l'horizon est
long, plus un changement a eu le temps de se produire) :

| Horizon | Modèle | MAE (lignes qui changent) | RMSE |
|---|---|---|---|
| t+30min | persistance | 2.386 | 4.030 |
| t+30min | LightGBM (niveau) | 2.105 | 3.342 |
| t+30min | LightGBM (variation) | 2.096 | 3.336 |
| t+30min | régression linéaire | 2.310 | 3.679 |
| t+60min | persistance | 2.846 | 4.432 |
| t+60min | LightGBM (niveau) | 2.546 | 4.001 |
| t+60min | LightGBM (variation) | 2.540 | 4.013 |
| t+60min | régression linéaire | 2.746 | 4.192 |

*(fichier complet : `ml/reports/metriques_stations_qui_changent.csv`)*

Sur ce sous-ensemble, **l'avantage de LightGBM sur la persistance est
beaucoup plus net** : -11,8 % de MAE à t+30 (2.105 vs 2.386), -10,5 % à
t+60 (2.546 vs 2.846) — contre -1,2 % et -2,6 % sur l'ensemble du test.
C'est la comparaison la plus honnête de la capacité du modèle à capter une
vraie dynamique plutôt qu'à bénéficier des lignes où ne rien prédire de
nouveau suffit.

**Arrondi à l'entier** (l'appli affiche un nombre entier de vélos) : sans
effet négatif, la MAE à t+30 passe de 1.420 à 1.384 pour LightGBM (niveau).

## 8. Erreur par heure de la journée

`erreur_par_heure_{30,60}min.png` (5 modèles) : persistance et les deux
LightGBM sont quasi confondus sur tout le graphe, moyenne_historique est
nettement au-dessus partout, régression linéaire légèrement au-dessus de
LightGBM/persistance. Pic d'erreur net aux heures de pointe (~7h-9h et
~17h-20h, heure Europe/Paris) pour **tous** les modèles, cohérent avec
l'analyse Phase 4 (flux domicile-travail) : ce sont les moments où la
disponibilité change le plus vite, donc les plus durs à prédire quel que
soit le modèle.

## 9. Classification « station vide dans 30 min » (seuil réglé sur validation)

> **Mise à jour du 16 novembre 2026** (modèle réentraîné, test 28 oct → 15 nov,
> 762 063 lignes). Seuils réglés sur validation : classifieur `proba >= 0.92`
> (F1 val 0.589), régression seuillée `niveau <= 1.25` (F1 val 0.559).
>
> | Modèle | Précision | Rappel | F1 |
> |---|---|---|---|
> | classifieur LightGBM | 0.612 | 0.462 | **0.527** |
> | régression seuillée | 0.511 | 0.510 | 0.510 |
> | persistance | 0.503 | 0.506 | 0.504 |
>
> Le classifieur dépasse la persistance de +4,4 % de F1 (précision nettement
> meilleure, rappel un peu plus bas). Le détail de méthode ci-dessous reste
> valable ; ses chiffres d'origine datent de `model-v1`.

**Ce que la Phase 5bis avait montré** (seuil naïf à 0.5, sans entraînement
dédié) : la persistance battait tous les modèles de régression sur le F1.
**Ce que la Phase 5ter corrige** : un vrai classifieur, et un seuil réglé
correctement, changent la conclusion.

### Méthode

Découpage à **trois niveaux**, strictement temporel (`ml/classify.py`) :

- **train_fit** : 2 482 553 lignes, du 2026-10-05 22:15 au 2026-10-23
  07:00 UTC — entraînement du classifieur et d'une régression dédiée
  (refaite sur train_fit, pour une comparaison équitable).
- **val** : 438 137 lignes, du 2026-10-23 07:15 au 2026-10-27 16:15 UTC
  — sert uniquement à régler le seuil de décision, **jamais vue à
  l'entraînement**.
- **test** : 731 821 lignes, du 2026-10-27 16:30 au 2026-11-01 22:45 UTC
  — identique au test principal, jamais vue avant l'évaluation finale.

**Déséquilibre de classes** : 135 060 positifs ("vide") / 2 347 493
négatifs dans train_fit (5.4%), traité via `scale_pos_weight=17.4` dans
`LGBMClassifier` (ratio négatifs/positifs).

**Seuils réglés sur val** (maximisation du F1, jamais sur le test) :
classifieur LightGBM → `proba ≥ 0.89` (F1 val = 0.576) ; régression
LightGBM seuillée → `niveau prédit ≤ 1.25` (F1 val = 0.539). Le seuil
optimal de la régression (1.25) confirme ce que la Phase 5bis avait
découvert empiriquement : 0.5 était un seuil arbitraire, pas optimal.

### Résultat sur le test (jamais vu ni à l'entraînement, ni pour régler le seuil)

| Modèle | Précision | Rappel | F1 |
|---|---|---|---|
| **classifieur LightGBM** | 0.527 | 0.466 | **0.495** |
| régression LightGBM seuillée | 0.505 | 0.467 | 0.486 |
| persistance | 0.466 | 0.467 | 0.466 |

*(fichier complet : `ml/reports/classification_station_vide_30min.csv`)*

**Conclusion révisée** : avec un classifieur dédié (déséquilibre géré) et
un seuil réglé honnêtement sur une validation jamais vue à l'entraînement,
**LightGBM bat désormais la persistance sur le F1** (0.495 vs 0.466,
+6.1%) — l'inverse de la conclusion naïve de la Phase 5bis. Leçon
méthodologique à retenir : comparer des probabilités/niveaux continus à
un seuil arbitraire (0.5) peut masquer la vraie performance d'un modèle ;
le seuil fait partie du modèle et doit être réglé comme un hyperparamètre,
sur une validation séparée du test.

Note : le classifieur et la régression dédiée de cette section ne sont
**pas persistés** (`ml/classify.py` les entraîne à la volée pour cette
comparaison) ni branchés sur l'API — seul le LightGBM niveau (§5) est
servi par `GET /stations/{id}/prediction`. Les brancher sur l'API
nécessiterait de fixer et sauvegarder leur seuil optimal, piste pour une
phase ultérieure si le cas d'usage "alerte" devient prioritaire.

## 10. Événement « devient vide » (bikes_t > 0 et cible == 0)

> **Mise à jour du 16 novembre 2026** (19 095 événements « devient vide »
> sur 723 116 lignes à `bikes_t > 0`) :
>
> | Modèle | Précision | Rappel | F1 |
> |---|---|---|---|
> | régression seuillée | 0.209 | 0.116 | **0.149** |
> | classifieur LightGBM | 0.314 | 0.003 | 0.007 |
> | persistance | 0 | 0 | 0 |
>
> Prévoir *l'instant où une station se vide* reste très difficile : la
> régression seuillée en détecte ~12 % (avec ~21 % de précision) et le
> classifieur, trop conservateur, presque aucun. À présenter comme un
> signal indicatif, pas comme une alerte fiable.

Restreint aux lignes où la station a encore des vélos au moment de la
prédiction (692 969 lignes sur 731 821 ; 20 670 d'entre elles
"deviennent vides" à t+30, soit 3.0%) :

| Modèle | Précision | Rappel | F1 |
|---|---|---|---|
| classifieur LightGBM | 0.332 | 0.027 | 0.051 |
| régression LightGBM seuillée | 0.209 | 0.087 | 0.123 |
| **persistance** | 0.000 | 0.000 | **0.000** |

*(fichier complet : `ml/reports/classification_devient_vide_30min.csv`)*

**F1 = 0 pour la persistance, confirmé comme attendu** : par
construction, la persistance prédit toujours "pas vide" quand
`bikes_t > 0` (elle recopie `bikes_t`, qui est non nul) — elle ne peut
donc *jamais* prédire l'événement "devient vide" sur ce sous-ensemble,
quel que soit le cas réel. Precision et rappel sont alors 0/0, ramenés à
0 par convention (`zero_division=0`).

Les deux modèles entraînés détectent l'événement, mais difficilement
(F1 0.05-0.12) — nettement plus dur que la classification "vide" globale
(F1 0.47-0.50, §9), ce qui est cohérent : prédire une **transition**
(un comportement qui bascule) est intrinsèquement plus dur que prédire un
**état stable**. Fait notable : ici la régression seuillée devance le
classifieur dédié (F1 0.123 vs 0.051) — l'inverse du résultat du §9 — à
confirmer sur une fenêtre de test plus longue avant d'en tirer une
conclusion ferme.

## 11. Second jeu de test : 2026-11-02 / 2026-11-03

> *Chiffres mesurés sur `model-v1` ; non recalculés pour le modèle du 16 novembre.*

### Pourquoi ces deux jours sont exclus du jeu principal

`backfill_day_quality` les marque non fiables (`max_gap_minutes` = 69.2
et 62.7 min, au-dessus du seuil de 60 min — voir
`ingestion/backfill.py`). En creusant plus précisément (horodatages bruts
de `station_status`) : ce ne sont pas des journées avec un seul trou
isolé, mais une collecte **uniformément clairsemée toute la journée**,
un relevé toutes les ~35-50 minutes au lieu de ~5 minutes habituellement
(24 à 26 trous > 30 min, répartis sur les 24h, les deux jours). Le
ré-échantillonnage à 15 min avec tolérance 30 min (voir §1) laisse donc
plus de trous (`NaN`) que sur les jours bien couverts.

### Sont-ils exploitables ? Oui, avec une réserve

Ce sont des **lundi et mardi ordinaires** (vérifié : `EXTRACT(ISODOW...)`
= 1 et 2 ; absents de `calendar_days`, donc ni fériés ni vacances
scolaires). `build_feature_table(..., include_unreliable=True)` y
construit **272 965 lignes** exploitables (un volume très correct malgré
la sparsité) — ajoutés comme second jeu de test, évalués avec les modèles
déjà entraînés sur la fenêtre principale (pas de ré-entraînement) :

| Horizon | Modèle | MAE | RMSE |
|---|---|---|---|
| t+30min | **persistance** | **1.256** | 2.825 |
| t+30min | LightGBM (niveau) | 1.545 | **2.650** |
| t+30min | LightGBM (variation) | 1.590 | 2.694 |
| t+30min | régression linéaire | 1.420 | 2.676 |
| t+60min | persistance | 1.975 | 3.698 |
| t+60min | **LightGBM (niveau)** | **1.933** | **3.194** |
| t+60min | LightGBM (variation) | 1.886 | 3.157 |
| t+60min | régression linéaire | 2.073 | 3.550 |

*(fichier complet : `ml/reports/metriques_test_2_3_novembre.csv`)*

**Résultat nuancé, à assumer honnêtement** : à t+30, **la persistance
gagne sur la MAE** (1.256 vs 1.545) mais **perd sur la RMSE** (2.825 vs
2.650) — LightGBM fait moins d'erreurs énormes mais une erreur moyenne
légèrement plus élevée. À t+60, LightGBM regagne l'avantage sur les deux
métriques. Hypothèse la plus probable : sur des données d'entrée plus
rares/bruitées (lags calculés à partir de relevés plus espacés), le
modèle — entraîné sur des jours à collecte dense — généralise un peu
moins bien à court terme que la persistance, qui ne dépend d'aucun
apprentissage et reste donc insensible à ce changement de régime de
collecte. C'est un signal utile : la qualité du modèle dépend aussi de la
régularité de la collecte au moment de l'inférence, pas seulement à
l'entraînement.

## 12. Évaluation sur données live (test réellement indépendant)

> *Chiffres mesurés sur `model-v1` ; non recalculés pour le modèle du 16 novembre.*

`ml/evaluate_live.py` ré-évalue les modèles sauvegardés sur notre propre
collecte en direct (`source = 'live'`, depuis le 2026-11-09 16:21 UTC) —
aucune de ces lignes n'a pu fuiter dans l'entraînement, qui s'arrête au
2026-11-01 (archive backfillée uniquement). C'est le test le plus
indépendant disponible : autre source, autre méthode de collecte (60s
chez nous vs ~5min pour l'archive), autre période.

Premier run, avec **4 449 lignes** disponibles (collecte démarrée il y a
quelques heures au moment de l'écriture de ce rapport) :

| Horizon | Modèle | MAE | RMSE |
|---|---|---|---|
| t+30min | **persistance** | **1.483** | 2.155 |
| t+30min | LightGBM (niveau) | 1.507 | **2.080** |
| t+60min | persistance | 2.053 | 3.026 |
| t+60min | LightGBM (niveau) | 2.057 | **2.874** |

*(fichier complet : `ml/reports/metriques_live.csv`)*

**À ce stade (quelques heures de live), résultat indicatif uniquement**
(sous le seuil de 1000 lignes que `ml/evaluate_live.py` considère fiable
— ici au-dessus, mais la fenêtre temporelle couverte reste très courte,
un seul après-midi). Le même motif qu'au §11 apparaît : MAE quasiment à
égalité (léger avantage persistance), RMSE nettement en faveur de
LightGBM. Cohérent avec un modèle qui réduit surtout les grosses erreurs.
**À relancer périodiquement** (`python -m ml.evaluate_live`, sans
modification) à mesure que la collecte live s'allonge, pour un vrai test
d'indépendance temporelle et de source.

## 13. Importance des variables (SHAP, LightGBM niveau)

Inchangé par rapport à la version précédente : `bikes_t` domine très
largement, puis `bikes_t_minus_15` ; météo et calendrier contribuent peu
sur cette fenêtre (automne, peu de jours fériés). Graphiques :
`shap_importance_{30,60}min.png`.

## 14. Limites

- **Une seule saison** (automne, 5 oct-1 nov 2026) : pas de généralisation
  garantie à l'été, l'hiver ou les vacances de Noël.
- **Test principal court** (~5 jours, 731k lignes) : gros volume mais peu
  de jours distincts — partiellement compensé par les deux tests
  complémentaires (2-3 novembre, §11 ; live, §12), qui pointent tous les
  deux la même nuance (avantage de LightGBM plus net en RMSE qu'en MAE,
  et plus net à t+60 qu'à t+30 sur données moins denses).
- **Cible agrégée** : vélos totaux uniquement, pas de modèle séparé
  mécanique/électrique.
- **Classification "devient vide"** (§10) : F1 encore faible (0.05-0.12)
  pour les deux modèles entraînés — la détection de transition reste un
  problème dur, non résolu ici.
- **Test live encore court** (§12, quelques heures à ce stade) : à
  re-vérifier en relançant `ml/evaluate_live.py` dans quelques jours.
- **Régression dédiée du §9/§10** : ré-entraînée sur `train_fit` (plus
  petit que le `train` complet) pour une comparaison équitable avec le
  classifieur — ses MAE/RMSE propres n'ont pas été recalculées
  séparément, seul son usage en classification (seuillée) est rapporté.
- **Contournement technique (sans impact sur la qualité)** : sur cette
  machine Windows, entraîner LightGBM et scikit-learn dans le même
  process, ou importer `matplotlib`/`shap` avant LightGBM, provoque un
  crash natif reproductible (conflit de runtimes OpenMP/BLAS).
  Contournements : LightGBM mono-thread (`n_jobs=1`), régression linéaire
  isolée en sous-process (`ml/_train_linear_worker.py`), imports différés
  après l'entraînement et après chaque nouvelle série de `.fit()`
  (`ml/classify.py` suit la même discipline que `ml/retrain.py`).
- **Historique backfillé tiers** : la majorité des données d'entraînement
  proviennent de l'archive communautaire ODbL `tibzsecondaire/velib-data`
  (voir README, section Attribution), pas de la collecte officielle
  directe.

## 15. Reproduire / ré-entraîner

```bash
python -m ml.retrain                        # fenêtre complète disponible
python -m ml.retrain --start 2026-10-05 --end 2026-11-02   # fenêtre figée (ce rapport)
python -m ml.evaluate_live                  # ré-évalue sur la collecte live à jour
```

Régénère les modèles (`ml/models/*.joblib`), toutes les métriques
(`ml/reports/metriques*.csv`, `ml/reports/classification_*.csv`)
et les graphiques. L'API expose les prédictions du modèle LightGBM niveau
via `GET /stations/{id}/prediction` (lit `ml/models/`, monté en volume
dans le conteneur `api`).
