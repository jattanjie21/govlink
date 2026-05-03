/**
 * Frontend-side metadata about publishing institutions. Keyed by the
 * slugified publisher string from `/datasets`. Missing entries fall
 * back to a generic description (and initials avatar).
 *
 * To add an institution: drop a logo at /public/logos/<slug>.png,
 * add an entry here keyed by the slug.
 */
export interface InstitutionMeta {
  description?: string;
  sector?: string;
  logoUrl?: string;
}

export const INSTITUTIONS: Record<string, InstitutionMeta> = {
  "central-bank-of-the-gambia": {
    sector: "Central bank",
    description:
      "The central bank and primary monetary authority of The Gambia. Issues currency, regulates the financial system, and publishes official daily valuation exchange rates.",
    logoUrl: "/logos/central-bank-of-the-gambia.png",
  },
};
