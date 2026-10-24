/**
 * frontend/src/utils/chemistry.js
 * Ion display and formula formatting per VirtuLab spec.
 * NO INVENTED CHEMISTRY (Hard Rule 2).
 */

export const CATIONS = {
  NA: { key: "NA", symbol: "Na+", formula: "Na", charge: "+", name: "sodium ion" },
  NH4: { key: "NH4", symbol: "NH4+", formula: "NH4", charge: "+", name: "ammonium ion" },
  CU: { key: "CU", symbol: "Cu2+", formula: "Cu", charge: "2+", name: "copper(II) ion" },
  FE2: { key: "FE2", symbol: "Fe2+", formula: "Fe", charge: "2+", name: "iron(II) ion" },
  FE3: { key: "FE3", symbol: "Fe3+", formula: "Fe", charge: "3+", name: "iron(III) ion" },
  AL: { key: "AL", symbol: "Al3+", formula: "Al", charge: "3+", name: "aluminium ion" },
  ZN: { key: "ZN", symbol: "Zn2+", formula: "Zn", charge: "2+", name: "zinc ion" },
  BA: { key: "BA", symbol: "Ba2+", formula: "Ba", charge: "2+", name: "barium ion" },
  CA: { key: "CA", symbol: "Ca2+", formula: "Ca", charge: "2+", name: "calcium ion" },
  MG: { key: "MG", symbol: "Mg2+", formula: "Mg", charge: "2+", name: "magnesium ion" },
  PB: { key: "PB", symbol: "Pb2+", formula: "Pb", charge: "2+", name: "lead(II) ion" },
};

export const ANIONS = {
  CL: { key: "CL", symbol: "Cl-", formula: "Cl", charge: "-", name: "chloride ion" },
  SO4: { key: "SO4", symbol: "SO4 2-", formula: "SO4", charge: "2-", name: "sulphate ion" },
  CO3: { key: "CO3", symbol: "CO3 2-", formula: "CO3", charge: "2-", name: "carbonate ion" },
  NO3: { key: "NO3", symbol: "NO3-", formula: "NO3", charge: "-", name: "nitrate ion" },
};

export const ION_DISPLAY_INFO = {
  // Cations
  NA: { key: "NA", type: "cation", formula: "Na", charge: "+", name: "sodium ion", tag: "Na+" },
  "Na+": { key: "NA", type: "cation", formula: "Na", charge: "+", name: "sodium ion", tag: "Na+" },

  NH4: { key: "NH4", type: "cation", formula: "NH4", charge: "+", name: "ammonium ion", tag: "NH4+" },
  "NH4+": { key: "NH4", type: "cation", formula: "NH4", charge: "+", name: "ammonium ion", tag: "NH4+" },

  CU: { key: "CU", type: "cation", formula: "Cu", charge: "2+", name: "copper(II) ion", tag: "Cu2+" },
  "Cu2+": { key: "CU", type: "cation", formula: "Cu", charge: "2+", name: "copper(II) ion", tag: "Cu2+" },

  FE2: { key: "FE2", type: "cation", formula: "Fe", charge: "2+", name: "iron(II) ion", tag: "Fe2+" },
  "Fe2+": { key: "FE2", type: "cation", formula: "Fe", charge: "2+", name: "iron(II) ion", tag: "Fe2+" },

  FE3: { key: "FE3", type: "cation", formula: "Fe", charge: "3+", name: "iron(III) ion", tag: "Fe3+" },
  "Fe3+": { key: "FE3", type: "cation", formula: "Fe", charge: "3+", name: "iron(III) ion", tag: "Fe3+" },

  AL: { key: "AL", type: "cation", formula: "Al", charge: "3+", name: "aluminium ion", tag: "Al3+" },
  "Al3+": { key: "AL", type: "cation", formula: "Al", charge: "3+", name: "aluminium ion", tag: "Al3+" },

  ZN: { key: "ZN", type: "cation", formula: "Zn", charge: "2+", name: "zinc ion", tag: "Zn2+" },
  "Zn2+": { key: "ZN", type: "cation", formula: "Zn", charge: "2+", name: "zinc ion", tag: "Zn2+" },

  BA: { key: "BA", type: "cation", formula: "Ba", charge: "2+", name: "barium ion", tag: "Ba2+" },
  "Ba2+": { key: "BA", type: "cation", formula: "Ba", charge: "2+", name: "barium ion", tag: "Ba2+" },

  CA: { key: "CA", type: "cation", formula: "Ca", charge: "2+", name: "calcium ion", tag: "Ca2+" },
  "Ca2+": { key: "CA", type: "cation", formula: "Ca", charge: "2+", name: "calcium ion", tag: "Ca2+" },

  MG: { key: "MG", type: "cation", formula: "Mg", charge: "2+", name: "magnesium ion", tag: "Mg2+" },
  "Mg2+": { key: "MG", type: "cation", formula: "Mg", charge: "2+", name: "magnesium ion", tag: "Mg2+" },

  PB: { key: "PB", type: "cation", formula: "Pb", charge: "2+", name: "lead(II) ion", tag: "Pb2+" },
  "Pb2+": { key: "PB", type: "cation", formula: "Pb", charge: "2+", name: "lead(II) ion", tag: "Pb2+" },

  // Anions
  CL: { key: "CL", type: "anion", formula: "Cl", charge: "-", name: "chloride ion", tag: "Cl-" },
  "Cl-": { key: "CL", type: "anion", formula: "Cl", charge: "-", name: "chloride ion", tag: "Cl-" },

  SO4: { key: "SO4", type: "anion", formula: "SO4", charge: "2-", name: "sulphate ion", tag: "SO4 2-" },
  "SO4 2-": { key: "SO4", type: "anion", formula: "SO4", charge: "2-", name: "sulphate ion", tag: "SO4 2-" },
  "SO4^2-": { key: "SO4", type: "anion", formula: "SO4", charge: "2-", name: "sulphate ion", tag: "SO4 2-" },

  CO3: { key: "CO3", type: "anion", formula: "CO3", charge: "2-", name: "carbonate ion", tag: "CO3 2-" },
  "CO3 2-": { key: "CO3", type: "anion", formula: "CO3", charge: "2-", name: "carbonate ion", tag: "CO3 2-" },
  "CO3^2-": { key: "CO3", type: "anion", formula: "CO3", charge: "2-", name: "carbonate ion", tag: "CO3 2-" },

  NO3: { key: "NO3", type: "anion", formula: "NO3", charge: "-", name: "nitrate ion", tag: "NO3-" },
  "NO3-": { key: "NO3", type: "anion", formula: "NO3", charge: "-", name: "nitrate ion", tag: "NO3-" },
  "NO3^-": { key: "NO3", type: "anion", formula: "NO3", charge: "-", name: "nitrate ion", tag: "NO3-" },
};

export const SALT_ITEMS = {
  nacl: { item: "nacl", cation: "NA", anion: "CL", formula: "NaCl", name: "Sodium Chloride" },
  nh4cl: { item: "nh4cl", cation: "NH4", anion: "CL", formula: "NH4Cl", name: "Ammonium Chloride" },
  cuso4: { item: "cuso4", cation: "CU", anion: "SO4", formula: "CuSO4", name: "Copper(II) Sulphate" },
  feso4: { item: "feso4", cation: "FE2", anion: "SO4", formula: "FeSO4", name: "Iron(II) Sulphate" },
  fecl3: { item: "fecl3", cation: "FE3", anion: "CL", formula: "FeCl3", name: "Iron(III) Chloride" },
  al2so43: { item: "al2so43", cation: "AL", anion: "SO4", formula: "Al2(SO4)3", name: "Aluminium Sulphate" },
  znso4: { item: "znso4", cation: "ZN", anion: "SO4", formula: "ZnSO4", name: "Zinc Sulphate" },
  bacl2: { item: "bacl2", cation: "BA", anion: "CL", formula: "BaCl2", name: "Barium Chloride" },
  caco3: { item: "caco3", cation: "CA", anion: "CO3", formula: "CaCO3", name: "Calcium Carbonate" },
  mgso4: { item: "mgso4", cation: "MG", anion: "SO4", formula: "MgSO4", name: "Magnesium Sulphate" },
  pbno32: { item: "pbno32", cation: "PB", anion: "NO3", formula: "Pb(NO3)2", name: "Lead(II) Nitrate" },
  nh42co3: { item: "nh42co3", cation: "NH4", anion: "CO3", formula: "(NH4)2CO3", name: "Ammonium Carbonate" },
};

/**
 * Decode a completion code like "VL-CU-SO4-XQMS-2X7P" into formula, name, cation, anion.
 * Returns null if invalid prefix or unrecognized cation/anion.
 */
export function decodeCompletionCode(rawCode) {
  if (!rawCode || typeof rawCode !== "string") return null;
  const clean = rawCode
    .replace(/[\u2010\u2011\u2012\u2013\u2014\u2212]/g, "-")
    .replace(/\s+/g, "")
    .toUpperCase();

  const parts = clean.split("-");
  if (parts.length < 3 || parts[0] !== "VL") return null;

  const cationKey = parts[1];
  const anionKey = parts[2];

  const cationMeta = CATIONS[cationKey];
  const anionMeta = ANIONS[anionKey];
  if (!cationMeta || !anionMeta) return null;

  const salt = Object.values(SALT_ITEMS).find(
    (s) => s.cation === cationKey && s.anion === anionKey
  );

  return {
    raw: rawCode,
    clean,
    cationKey,
    anionKey,
    cation: cationMeta,
    anion: anionMeta,
    formula: salt ? salt.formula : `${cationKey}${anionKey}`,
    name: salt ? salt.name : `${cationMeta.name} ${anionMeta.name}`,
    nonce: parts[3] || "",
    chk: parts[4] || "",
    isFullCode: parts.length === 5 && (parts[3] || "").length === 4 && (parts[4] || "").length === 4,
  };
}

