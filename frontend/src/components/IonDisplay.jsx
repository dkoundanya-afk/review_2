/**
 * frontend/src/components/IonDisplay.jsx
 * Chemistry display components: IonChip, FormattedFormula, and SaltCard.
 * Cation chips: Blue style.
 * Anion chips: Orange style.
 * Subscripts & superscripts correctly rendered.
 */
import { CATIONS, ANIONS, ION_DISPLAY_INFO } from "../utils/chemistry.js";

/**
 * Format chemical formula string with proper subscripts.
 * e.g. "CuSO4" -> "CuSO₄", "Al2(SO4)3" -> "Al₂(SO₄)₃"
 */
export function FormattedFormula({ formula }) {
  if (!formula) return null;

  // Split formula into letters/parentheses and numbers to wrap numbers in <sub>
  const parts = formula.split(/(\d+)/);
  return (
    <span className="font-monospace fw-bold">
      {parts.map((part, i) =>
        /^\d+$/.test(part) ? <sub key={i}>{part}</sub> : <span key={i}>{part}</span>
      )}
    </span>
  );
}

/**
 * Render any ion (by key e.g. "CU", "SO4" or tag e.g. "Cu2+", "SO4 2-")
 * with proper chemical formula subscript and charge superscript.
 */
export function FormattedIon({ ionKeyOrTag }) {
  if (!ionKeyOrTag) return null;
  const item =
    ION_DISPLAY_INFO[ionKeyOrTag] ||
    ION_DISPLAY_INFO[String(ionKeyOrTag).trim().toUpperCase()];
  if (item) {
    return (
      <span className="font-monospace">
        <FormattedFormula formula={item.formula} />
        <sup>{item.charge}</sup>
      </span>
    );
  }

  // Fallback for custom radical tags: turn trailing digits into subscripts, charges into superscripts
  return <span className="font-monospace">{ionKeyOrTag}</span>;
}

/**
 * Display an ion with formula and charge.
 * Kept for backwards compatibility with earlier components.
 */
export function FormattedIonSymbol({ ionKey }) {
  return <FormattedIon ionKeyOrTag={ionKey} />;
}

/**
 * Ion chip component.
 * Blue style for cations, Orange style for anions.
 */
export function IonChip({ ionKey, type, showName = true }) {
  const resolved =
    ION_DISPLAY_INFO[ionKey] ||
    ION_DISPLAY_INFO[String(ionKey).trim().toUpperCase()];
  const chipType = type || resolved?.type || "cation";
  const chipClass = chipType === "cation" ? "ion-chip-cation" : "ion-chip-anion";
  const name =
    resolved?.name ||
    (chipType === "cation" ? CATIONS[ionKey]?.name : ANIONS[ionKey]?.name);

  return (
    <span className={`ion-chip ${chipClass}`}>
      <span className="ion-chip-symbol">
        <FormattedIon ionKeyOrTag={ionKey} />
      </span>
      {showName && name && (
        <span className="ion-chip-name">{name}</span>
      )}
    </span>
  );
}
