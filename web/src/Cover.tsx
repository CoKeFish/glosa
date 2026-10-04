/** Generated cover for imported books: dark tile with the title, like library thumbnails. */
const PALETTES = [
  ["#15233b", "#24406b"],
  ["#1d2b22", "#2f5a40"],
  ["#2d1b33", "#5a3466"],
  ["#33221a", "#6b4127"],
  ["#14303a", "#1f5f6e"],
  ["#2a2a35", "#4a4a63"],
];

function hash(text: string): number {
  let h = 0;
  for (const ch of text) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return h;
}

export function Cover({ title, size = "md" }: { title: string; size?: "sm" | "md" }) {
  const [a, b] = PALETTES[hash(title) % PALETTES.length];
  const words = title.split(/\s+/);
  const last = words.pop();
  return (
    <div className={`cover cover-${size}`} style={{ background: `linear-gradient(145deg, ${a}, ${b})` }}>
      {size === "md" ? (
        <span>
          {words.join(" ")} <em>{last}</em>
        </span>
      ) : (
        <span>{title.slice(0, 1).toUpperCase()}</span>
      )}
    </div>
  );
}
