// Stable colour assignments per label system. Known labels use the "atlas" palette
// (filled marks); discovered communities use a separate "ink" palette and are
// always titled as discovered by Louvain in legends.

export const REGION_ORDER = [
  "Northern Europe", "Western Europe", "Southern Europe", "Eastern Europe",
  "Western Asia", "Southern Asia", "Eastern Asia", "South-Eastern Asia",
  "Northern Africa", "Sub-Saharan Africa", "Northern America", "Latin America and the Caribbean", "Melanesia",
];

// Hue families by continent (blues for Europe, ochres/reds for Asia, browns for Africa,
// greens for the Americas, violet for Oceania), varied in lightness.
export const REGION_COLOURS: Record<string, string> = {
  "Northern Europe": "#2f5f8f",
  "Western Europe": "#5b8fc4",
  "Southern Europe": "#1f8a8a",
  "Eastern Europe": "#7d9fb8",
  "Western Asia": "#c0632f",
  "Southern Asia": "#d9952b",
  "Eastern Asia": "#a33a3a",
  "South-Eastern Asia": "#e0b85c",
  "Northern Africa": "#8a6239",
  "Sub-Saharan Africa": "#5e4425",
  "Northern America": "#3d7a3d",
  "Latin America and the Caribbean": "#88b04b",
  "Melanesia": "#8a5aa8",
};

export const ATU_CHAPTER_ORDER = [
  "Animal Tales", "Tales of Magic", "Religious Tales", "Realistic Tales (Novelle)",
  "Tales of the Stupid Ogre", "Anecdotes and Jokes", "Formula Tales",
];
export const ATU_CHAPTER_COLOURS: Record<string, string> = {
  "Animal Tales": "#3d7a3d",
  "Tales of Magic": "#6a4fa3",
  "Religious Tales": "#b07d2b",
  "Realistic Tales (Novelle)": "#2f6f9f",
  "Tales of the Stupid Ogre": "#a33a3a",
  "Anecdotes and Jokes": "#d07a2e",
  "Formula Tales": "#4c8a8a",
};

// Discovered communities: muted jewel tones; small communities fall back to grey.
export const COMMUNITY_COLOURS = [
  "#7b3f61", "#2f6b4f", "#b0662a", "#3d5a99", "#8f8a2e", "#5e3c99", "#a23b3b", "#2a7f8a",
  "#9c6b98", "#5b7f2e", "#c08a4a", "#4b6f8f",
];
export const UNKNOWN = "#b9b2a5";
export const SMALL_COMMUNITY = "#cbc3b4";

export function communityColour(colourIndex: number, size: number): string {
  if (size < 5) return SMALL_COMMUNITY;
  return COMMUNITY_COLOURS[colourIndex % COMMUNITY_COLOURS.length] ?? SMALL_COMMUNITY;
}

export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
