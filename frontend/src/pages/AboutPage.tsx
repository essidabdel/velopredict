import { AlertTriangle, BookOpen, BrainCircuit, Database, Info } from "lucide-react";

function Ext({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a href={href} target="_blank" rel="noreferrer">
      {children}
    </a>
  );
}

export function AboutPage() {
  return (
    <div className="about-page" style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}>
      <h1 className="page-title">
        <span className="page-title-icon">
          <Info size={22} />
        </span>
        À propos
      </h1>

      <section className="card">
        <h2 className="section-title">
          <BookOpen size={18} />
          Le projet
        </h2>
        <p style={{ margin: 0 }}>
          VéloPredict prédit la disponibilité des vélos Vélib' à 30 et 60 minutes, station par
          station. Projet réalisé pour le module Open Data (IPSSI).
        </p>
      </section>

      <section className="card">
        <h2 className="section-title">
          <Database size={18} />
          Données
        </h2>
        <p style={{ margin: 0, lineHeight: 1.8 }}>
          <Ext href="https://velib-metropole-opendata.smovengo.cloud/opendata/Velib_Metropole/gbfs.json">
            Vélib' Métropole (GBFS temps réel)
          </Ext>{" "}
          · <Ext href="https://open-meteo.com/">Open-Meteo</Ext> · Jours fériés et vacances
          scolaires (<Ext href="https://calendrier.api.gouv.fr/">api.gouv.fr</Ext>,{" "}
          <Ext href="https://data.education.gouv.fr/">data.education.gouv.fr</Ext>) · Géocodage des
          communes (<Ext href="https://geo.api.gouv.fr/">geo.api.gouv.fr</Ext>) · Historique : archive{" "}
          <Ext href="https://github.com/tibzsecondaire/velib-data">tibzsecondaire/velib-data</Ext>{" "}
          (<Ext href="https://opendatacommons.org/licenses/odbl/1-0/">ODbL 1.0</Ext>) · Fonds de
          carte{" "}
          <Ext href="https://www.openstreetmap.org/copyright">© contributeurs OpenStreetMap</Ext>.
        </p>
      </section>

      <section className="card">
        <h2 className="section-title">
          <BrainCircuit size={18} />
          Modèle
        </h2>
        <p style={{ margin: 0 }}>
          LightGBM entraîné sur un découpage temporel, à partir de l'heure, du calendrier, de la
          météo et de la disponibilité récente. Le niveau de risque (faible, moyen, élevé) découle de
          la prédiction à 30 minutes.
        </p>
      </section>

      <section className="card">
        <h2 className="section-title">
          <AlertTriangle size={18} />
          Limites
        </h2>
        <p style={{ margin: 0 }}>
          Le modèle est entraîné sur une seule saison (automne) et les niveaux de risque reposent sur
          des seuils, pas sur des probabilités calibrées ; une station récente ou sans flux peut ne
          pas avoir de prévision. <strong>Une prévision, pas une certitude.</strong>
        </p>
      </section>
    </div>
  );
}
