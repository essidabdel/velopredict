export function AboutPage() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      <h1 className="page-title">À propos</h1>

      <section className="card">
        <h2 className="section-title">Le projet</h2>
        <p>
          VéloPredict prédit la disponibilité des vélos Vélib' (Paris et communes
          voisines) à 30 et 60 minutes, station par station, à partir de données
          ouvertes collectées en temps réel. Projet réalisé dans le cadre du
          module Open Data (IPSSI).
        </p>
      </section>

      <section className="card">
        <h2 className="section-title">Sources de données (open data)</h2>
        <ul style={{ paddingLeft: "1.2em", lineHeight: 1.7 }}>
          <li>
            <strong>Vélib' Métropole — GBFS</strong> (temps réel, sans clé) :{" "}
            <a
              href="https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/gbfs.json"
              target="_blank"
              rel="noreferrer"
            >
              flux officiel
            </a>{" "}
            (disponibilité des vélos mécaniques/électriques, bornes libres,
            informations stations).
          </li>
          <li>
            <strong>Open-Meteo</strong> : prévisions et historique météo pour Paris.
          </li>
          <li>
            <strong>Jours fériés</strong> : calendrier.api.gouv.fr.
          </li>
          <li>
            <strong>Vacances scolaires</strong> : data.education.gouv.fr (zone C).
          </li>
          <li>
            <strong>Géocodage commune/arrondissement</strong> : geo.api.gouv.fr.
          </li>
        </ul>
      </section>

      <section className="card">
        <h2 className="section-title">Attribution — historique backfillé</h2>
        <p>
          Le flux GBFS officiel Vélib' est un instantané temps réel : il n'expose
          aucun historique. Pour disposer de plusieurs semaines de données réelles
          dès le lancement du projet, l'historique est complété par l'archive
          communautaire{" "}
          <a href="https://github.com/tibzsecondaire/velib-data" target="_blank" rel="noreferrer">
            tibzsecondaire/velib-data
          </a>
          , qui republie en continu les mêmes données officielles GBFS Vélib'
          Métropole, sous licence{" "}
          <a href="https://opendatacommons.org/licenses/odbl/1-0/" target="_blank" rel="noreferrer">
            Open Database License (ODbL) 1.0
          </a>{" "}
          — la même licence que le jeu de données officiel publié par la Ville de
          Paris sur data.gouv.fr. Les cartes utilisent les fonds{" "}
          <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
            © contributeurs OpenStreetMap
          </a>
          .
        </p>
      </section>

      <section className="card">
        <h2 className="section-title">Méthode du modèle de prédiction</h2>
        <p>
          Modèle LightGBM entraîné sur un découpage strictement temporel (jamais
          aléatoire) : entraînement sur les premiers jours, test sur les derniers,
          pour éviter toute fuite d'information. Variables utilisées : heure, jour
          de semaine, week-end, jour férié, vacances scolaires, météo,
          disponibilité récente (t, t-15, t-30, t-60), capacité et position de la
          station. Comparé à deux références simples (persistance et moyenne
          historique par station/heure/jour), et à une régression linéaire.
        </p>
        <p>
          Le niveau de risque affiché sur chaque fiche station ("faible", "moyen",
          "élevé") est calculé à partir de la prédiction à 30 minutes — jamais
          affiché comme une probabilité brute.
        </p>
      </section>

      <section className="card">
        <h2 className="section-title">Limites</h2>
        <ul style={{ paddingLeft: "1.2em", lineHeight: 1.7 }}>
          <li>Modèle entraîné sur une seule saison (automne) : pas de garantie de généralisation à l'été ou l'hiver.</li>
          <li>La cible prédite est le nombre total de vélos (mécaniques + électriques combinés), pas un détail par type.</li>
          <li>
            Le niveau de risque "station vide" repose sur des seuils réglés sur un
            jeu de validation, pas une probabilité calibrée à l'usage individuel.
          </li>
          <li>
            Une station nouvelle ou dont le flux GBFS est interrompu peut ne pas
            avoir de prédiction disponible.
          </li>
        </ul>
        <p className="text-muted" style={{ fontSize: "0.85rem", marginBottom: 0 }}>
          Détail complet des métriques et de la méthode : voir{" "}
          <code>ml/reports/RESULTATS.md</code> dans le dépôt du projet.
        </p>
      </section>
    </div>
  );
}
