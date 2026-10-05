---
name: glosa
description: A free, open source reader for learning languages from your own books, on your own computer.
colors:
  cover: "#1f2fd1"
  cover-deep: "#1726a8"
  paper: "#f6f7f8"
  paper-edge: "#e1e4e9"
  slip-white: "#ffffff"
  ink: "#1c1b19"
  ink-2: "#3d3c39"
  pencil: "#4a4945"
  highlighter-yellow: "#ffe94a"
  highlighter-blue: "#a5ddff"
  highlighter-pink: "#ffa3cc"
  flag-orange: "#ffb36b"
typography:
  display:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "clamp(2.7rem, 1.3rem + 5.4vw, 6rem)"
    fontWeight: 650
    lineHeight: 1.02
    letterSpacing: "-0.025em"
    fontVariation: "\"opsz\" 72"
  headline:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "clamp(1.9rem, 1.3rem + 2.2vw, 3.1rem)"
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: "-0.02em"
    fontVariation: "\"opsz\" 60"
  title:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "clamp(1.4rem, 1.1rem + 1.4vw, 2.3rem)"
    fontWeight: 400
    lineHeight: 1.3
  body:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "clamp(1.02rem, 0.96rem + 0.25vw, 1.16rem)"
    fontWeight: 400
    lineHeight: 1.62
  passage:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "clamp(1.15rem, 1.02rem + 0.55vw, 1.5rem)"
    fontWeight: 400
    lineHeight: 1.85
  running-head:
    fontFamily: "Literata, Iowan Old Style, Georgia, serif"
    fontSize: "0.92rem"
    fontWeight: 400
    letterSpacing: "0.04em"
    fontFeature: "\"smcp\""
  gloss:
    fontFamily: "Reenie Beanie, Segoe Print, cursive"
    fontSize: "clamp(1.6rem, 1.35rem + 0.6vw, 2rem)"
    fontWeight: 400
    lineHeight: 1.15
  label:
    fontFamily: "Schibsted Grotesk, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.95rem"
    fontWeight: 600
  code:
    fontFamily: "ui-monospace, Cascadia Mono, SF Mono, Consolas, monospace"
    fontSize: "0.92rem"
    lineHeight: 1.6
rounded:
  flag: "2px"
  control: "3px"
  page: "4px"
spacing:
  edge: "clamp(8px, 1.6vw, 22px)"
  margin-column: "clamp(190px, 22vw, 300px)"
  gutter: "clamp(24px, 4vw, 64px)"
  leaf-inline: "clamp(20px, 6vw, 96px)"
  leaf-top: "clamp(28px, 4vw, 56px)"
  leaf-bottom: "clamp(40px, 5vw, 72px)"
components:
  button-cover:
    backgroundColor: "{colors.cover}"
    textColor: "{colors.slip-white}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0.7rem 1rem"
  button-cover-hover:
    backgroundColor: "{colors.cover-deep}"
  button-paper:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.cover}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0.7rem 1rem"
  button-paper-hover:
    backgroundColor: "{colors.slip-white}"
  button-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    padding: "0.7rem 1rem"
  button-line-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
  page-flag:
    backgroundColor: "{colors.flag-orange}"
    textColor: "{colors.ink}"
    rounded: "{rounded.flag}"
    padding: "0.45rem 0.7rem 0.45rem 0.85rem"
    width: "5.8rem"
  bookmark:
    backgroundColor: "{colors.cover}"
    textColor: "{colors.slip-white}"
    padding: "1.2rem 1.1rem 2.6rem"
    width: "max(clamp(190px, 22vw, 300px), 300px)"
  code-block:
    backgroundColor: "#eaedf1"
    textColor: "{colors.ink}"
    typography: "{typography.code}"
    rounded: "{rounded.control}"
    padding: "0.8rem 1rem"
  errata-slip:
    backgroundColor: "{colors.slip-white}"
    textColor: "{colors.ink-2}"
    padding: "1rem 1.2rem 1.1rem"
  toast:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "0.6rem 1rem"
---

# Design System: glosa

## Overview

**Creative North Star: "The Annotated Paperback"**

glosa presents itself the way its readers read: a pocket paperback page in cool white, a real book face, fluorescent highlighter on the words that matter and graphite pencil glosses in the margin. The page sits on an ultramarine cover that shows at the edges and closes the book at the end, drenched. Every structural device is borrowed from the book rather than from software: running heads and folios instead of a header bar, page flags on the fore-edge instead of a nav, a bookmark slip instead of a CTA card, an index instead of a feature grid, an errata slip instead of a roadmap, an appendix instead of a docs section.

Density is that of a well-set book: one generous text column, a margin column for notes, long measure-limited lines, quiet hierarchy. Colour is almost absent from the paper; it arrives only as highlighter ink, and each ink means one thing. The world refuses the open-source default of a split hero with an app screenshot over a grid of feature cards, and refuses the SaaS register (gradients, sales tone) and the gamified one (mascots, toy colours).

Scope: this system governs the landing page (`landing/`) and the brand mark everywhere. The app UI (`web/`) is out of scope except for the mark: its favicon (`web/src/icon.svg`) and header wordmark (`web/src/wordmark.svg`, rendered in currentColor at 30px high) belong to this system; its own tokens (DM Sans, its greens, blues and yellows) are a separate, deliberately unchanged system and must not be reconciled with this one.

**Key Characteristics:**
- Paper on cover: a cool white page with a faint fractal-noise grain, sitting on ultramarine.
- Three highlighter inks with fixed meanings; no other colour on the paper.
- Literata does all reading and display work; Reenie Beanie is the pencil; Schibsted Grotesk only labels controls.
- Book apparatus as interface: running heads, folios, glosses keyed by superscript numbers, page flags, bookmark, index, errata, appendix, back cover.
- Soft, paper-object shadows; small, nearly square corners.

## Colors

A near-colourless page on a saturated ultramarine cover, with fluorescent inks that only ever mean something.

### Primary
- **Ultramarine Cover** (cover): the book's cloth. Shows as the margin around the page, fills the bookmark, the primary button and the whole back cover; also the browser theme colour and the focus ring on paper.
- **Deep Cover** (cover-deep): hover state of cover-filled buttons and the scrollbar thumb.

### Secondary
- **Highlighter Yellow** (highlighter-yellow): the brand ink. The stroke behind the wordmark, words being learned, the highlighted words in the headline and deck, and text selection.
- **Highlighter Blue** (highlighter-blue): new words only.
- **Highlighter Pink** (highlighter-pink): expressions only.

### Tertiary
- **Flag Orange** (flag-orange): page flags on the fore-edge, which are the navigation. Never used as a highlighter.

### Neutral
- **Cool Paper** (paper): the page surface, the paper button on the cover, the label pasted on the back cover.
- **Paper Edge** (paper-edge): running-head rules and the dashed rule between leaves.
- **Slip White** (slip-white): the errata slip tucked into the book, and text on the cover.
- **Ink** (ink): body text, headings, the wordmark letters, the icon's g.
- **Second Ink** (ink-2): running heads, leads, index sub-entries, errata body.
- **Graphite Pencil** (pencil): handwritten glosses, gloss markers, folios, index letters, notes.

### Named Rules
**The Ink Means Something Rule.** Yellow is learning (and the brand), blue is new, pink is an expression. A highlighter colour never decorates; if a word is highlighted, the colour states its status, and the legend must be able to explain it.

**The Cover Frames Rule.** Ultramarine is the binding, not a page colour: it appears at the page edges, on objects that belong to the cover (bookmark, back cover, cover-filled button) and nowhere as a paper tint or gradient.

## Typography

**Display Font:** Literata (with Iowan Old Style, Georgia, serif), variable optical size, weights 400-800, italics 400-600, self-hosted.
**Body Font:** Literata, same family.
**Hand Font:** Reenie Beanie (with Segoe Print, cursive), the pencil.
**Label Font:** Schibsted Grotesk (with ui-sans-serif, system-ui), buttons, flags, bookmark, toast and colophon only.
**Code Font:** system monospace stack (ui-monospace, Cascadia Mono, SF Mono, Consolas).

**Character:** a book typeset properly, with a reader's pencil in the margin. The serif carries everything that is read; the grotesk only appears on things you press; the hand only on notes a reader would write.

### Hierarchy
- **Display** (650, clamp 2.7rem to 6rem, 1.02, opsz 72, balanced): the headline, set as book text at display size, with highlighted words.
- **Headline** (600, clamp 1.9rem to 3.1rem, 1.08, opsz 60): chapter titles on each leaf.
- **Title** (italic 400, clamp 1.4rem to 2.3rem, 1.3): the back-cover blurb.
- **Deck / Lead** (400, clamp 1.18rem to 1.45rem at 1.5 for the deck; 1.1rem to 1.3rem in second ink for leads; 34-36em measure).
- **Body** (400, clamp 1.02rem to 1.16rem, 1.62): running text, promises with first-line indents (1.4em, none on the first paragraph), index entries.
- **Passage** (400, clamp 1.15rem to 1.5rem, 1.85, 32em measure): the annotated reading sample; drop cap at 3.6em, weight 600; hanging punctuation.
- **Running head** (small caps, 0.92rem, 0.04em tracking, second ink): top of every leaf, wordmark or section name on either side of a hairline rule. Folios: centred, 0.85rem, old-style numerals, pencil.
- **Gloss** (Reenie Beanie 400, clamp 1.6rem to 2rem, 1.15, pencil): margin notes, legend, the "try it" note, step numbers (2.1rem); keyed by superscript hand numbers in the text (1.35em, raised 0.4em).
- **Label** (Schibsted Grotesk 600, 0.95rem buttons, 0.78rem flags at 0.02em tracking).
- **Small-caps heads** (Literata small caps 600-700, about 1rem, 0.04-0.05em): bookmark title, errata title, index letters, promise lead-ins.

### Named Rules
**The Book Face Rule.** Anything that is read is set in Literata. The grotesk never sets a heading or a paragraph; it labels controls.

**The Pencil Is a Reader Rule.** Reenie Beanie only writes what a reader would write in a margin: glosses, keys, a legend, a note to try something, step numbers. It never sets a heading, a button or product copy that the book itself would print.

## Layout

The page is a single sheet laid on the cover: inset from the viewport by the cover edge (clamp 8px to 22px) at top and sides, top corners 4px, running to the bottom where the back cover takes over. The page is divided into leaves separated by a dashed paper-edge rule; each leaf has a running head at the top and a folio at the bottom, and is padded clamp 28-56px top, 20-96px sides, 40-72px bottom.

Inside a leaf, a two-column text grid: a fluid text column and a margin column (clamp 190px to 300px) with a gutter of clamp 24px to 64px. Glosses live in the margin column, aligned to the top of the text. Text measures stay book-like (32-36em for passages and leads, 22em for the blurb). The index sets in two columns of at least 17rem, entries with a 1.2em hanging indent and letter rows that never break from their entries.

The bookmark hangs from the top edge of the first leaf over the margin column (at least 300px wide); the first leaf's glosses start below it. Page flags are fixed to the right viewport edge, vertically centred, tucked 1.4rem off-screen and sliding out on hover.

At 860px and below: one column; glosses fall under the text; the bookmark becomes an in-flow slip at the top of the first leaf; page flags become a row of tabs sticking up from the top of the page (top corners rounded, no shadow); the page loses its top cover margin.

## Elevation & Depth

Depth is physical, never interface: every shadow belongs to a paper object resting on another (page on cover, slip on page, label on cloth). Shadows are soft, neutral black at low opacity, offset downward; none are coloured or hard-edged. The page itself carries a faint grain (fractal noise at 5% alpha) and an inner shadow on its right edge suggesting the spine curve.

### Shadow Vocabulary
- **Page on cover** (`box-shadow: inset -14px 0 18px -16px rgb(0 0 0 / 0.22), 0 10px 30px rgb(0 0 0 / 0.28)`): the one page.
- **Bookmark** (`box-shadow: 0 8px 18px rgb(0 0 0 / 0.22)`): the hanging slip.
- **Tucked slip** (`box-shadow: 0 3px 10px rgb(0 0 0 / 0.12)`): the errata slip, rotated -1.4deg.
- **Pasted label** (`box-shadow: 0 2px 6px rgb(0 0 0 / 0.25)`): the title label on the back cover, rotated -1deg.
- **Page flag** (`box-shadow: -1px 1px 3px rgb(0 0 0 / 0.18)`): flags on the fore-edge (dropped on mobile).

### Named Rules
**The Paper Objects Rule.** A shadow is allowed only when something is physically lying on something else. Buttons, the code well and the toast are flat.

**The Slight Hand Rule.** Loose paper and pencil are never perfectly straight: slips rotate about 1-1.4deg, glosses alternate -1.2deg and 0.8deg. Printed text is never rotated.

## Shapes

Nearly square, like paper and card: 2px on flags (only the side that leaves the page), 3px on buttons, code wells and the toast, 4px on the top corners of the page. The bookmark is cut with a swallowtail notch (clip-path to 1.3rem deep at the centre of its bottom edge). The highlighter mark is a skewed band rather than a box: a 100deg gradient with feathered ends, 0.82em tall at 72% of the line (0.62em at 86% in the display headline), with uneven corners (0.2em 0.08em 0.24em 0.06em) and cloned across line breaks. The app icon is a 64-unit cool-paper tile with 14-unit corners, a yellow highlighter stroke and an ink Literata g.

## Components

### Buttons
Tactile and quiet, set in the grotesk; they look like printed controls, not app chrome.
- **Shape:** gently squared (3px).
- **Cover button:** ultramarine with white text, on paper (the appendix copy action); hover deepens to cover-deep.
- **Paper button:** cool paper with ultramarine text, on the cover (bookmark copy action, full width there; back-cover GitHub link); hover goes to white.
- **Line button:** transparent with a 1.5px inset ink outline, on paper; hover inverts to ink fill and paper text.
- **Ghost button:** transparent with a 1.5px inset white outline at 70%, on the cover; hover adds a 12% white wash.
- **States:** press nudges down 1px (0.15s, expo-out); focus is a 2.5px outline offset 3px. Icons are inline 1.05em stroke SVGs (copy, GitHub).

### Page Flags (navigation)
Neon sticky flags stuck to the fore-edge of the book, one per section plus the language toggle. Orange, ink label, 0.78rem grotesk 600, 5.8rem wide, tucked 1.4rem past the viewport edge and sliding out to 0.4rem on hover or focus (0.25s expo-out). On mobile they become tabs on top of the page and lift 2px on hover.

### Bookmark
The primary action. An ultramarine slip hanging from the top edge of the first leaf with a swallowtail notch, a small-caps serif title in pale periwinkle, the install commands in monospace white with dimmed prompts, a full-width paper copy button and a plain GitHub link.

### Highlighter Mark
The signature. A skewed fluorescent band behind a word or phrase in one of the three inks. On first view, marks sweep in left to right in reading order (0.55s expo-out, 110ms stagger), once; with reduced motion they are simply present. In the sample passage the marks are interactive: clicking a word cycles new (blue), learning (yellow), known (no mark); expressions (pink) are fixed.

### Pencil Gloss
A handwritten margin note in graphite, keyed to the text by a raised hand-written number, with the glossed word set in ink. Lists of glosses stack with 1.1rem gaps and alternate a slight tilt.

### Running Head and Folio
A small-caps line at the top of every leaf: the wordmark (1.9rem high) or the book's subtitle on one side, a hairline paper-edge rule filling the middle, the section name on the other. A centred old-style folio closes each leaf.

### Index
The feature list as a book index: small-caps letter rows in pencil, terms in Literata 650, a comma, the locator text, and an indented sub-entry in second ink; "see also" in pencil italic.

### Slips and Labels
The errata slip (white, rotated, tucked shadow, small-caps title) carries what is not yet built. The back cover carries the wordmark on a pasted paper label, an italic blurb, buttons, and a colophon in the grotesk (0.85rem, pale periwinkle on a 25% white hairline).

### Code Well
Commands in the system monospace on a cool grey well (3px, 0.8rem 1rem); the `$` prompt is dimmed and unselectable.

### Toast
Ink pill-less rectangle (3px) with paper text, rising 20px and fading in at the bottom centre for copy confirmation, polite live region.

## Do's and Don'ts

### Do:
- **Do** set every word that is read in Literata, using its optical sizes (opsz 72 for display, 60 for chapter heads).
- **Do** give each highlighter ink exactly one meaning: yellow learning and brand, blue new, pink expression.
- **Do** borrow structure from the book: running heads, folios, margin glosses, page flags, bookmark, index, errata, appendix, back cover.
- **Do** keep the page cool paper (#f6f7f8 family) framed by the ultramarine cover, with the cover returning in full at the end.
- **Do** key every pencil gloss to its word with a raised hand-written number.
- **Do** keep shadows soft and tied to a physical object (page, slip, label, flag).
- **Do** use the wordmark in currentColor over its fixed yellow stroke, and the icon tile as the favicon everywhere, including the app.

### Don't:
- **Don't** use a highlighter colour decoratively, as a background tint, or for a fourth meaning; and don't use flag orange as a highlighter.
- **Don't** put gradients, glow, or coloured shadows on the page or the cover.
- **Don't** set headings, buttons or printed product copy in Reenie Beanie.
- **Don't** replace the book apparatus with a split hero, an app screenshot, or a grid of feature cards.
- **Don't** apply this system's palette or type to the app UI; only the mark crosses over.
