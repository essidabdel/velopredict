import { ETAT_COLORS } from "../constants/etat";
import type { EtatStation } from "../api/types";
import { formatNumber } from "../lib/format";

// « 24 / 51 vélos » avec une jauge de remplissage de la station.
export function FillGauge({
  bikes,
  capacity,
  etat,
}: {
  bikes: number;
  capacity: number;
  etat: EtatStation;
}) {
  const pct = capacity > 0 ? Math.min(100, Math.round((bikes / capacity) * 100)) : 0;
  return (
    <div className="fill-gauge">
      <div className="fill-gauge-text">
        <span className="fill-gauge-big">{formatNumber(bikes)}</span>
        <span className="text-secondary"> / {formatNumber(capacity)} vélos</span>
      </div>
      <div
        className="fill-gauge-track"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={capacity}
        aria-valuenow={bikes}
        aria-label={`${bikes} vélos sur ${capacity} places`}
      >
        <div className="fill-gauge-bar" style={{ width: `${pct}%`, background: ETAT_COLORS[etat] }} />
      </div>
    </div>
  );
}
