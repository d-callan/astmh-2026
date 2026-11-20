# ASTMH 2026 — Slide Decks

Slide decks from the 2026 ASTMH annual meeting, published as a static GitHub Pages site.

## Decks

| Deck | Talk | Presenter |
| --- | --- | --- |
| `astmh-brc-ai-intro-slides.html` | BRC-Analytics — AI + Galaxy + Infrastructure | Anton Nekrutenko (Penn State) |
| `astmh-intro-slides.html` | BRC Analytics — Symposium Introduction | Anton Nekrutenko (Penn State) |
| `astmh-malaria-slides.html` | Your Pathogen Question. A Reproducible Analysis. | Ananias A. Escalante (Temple University) |
| `astmh-logan-slides.html` | Query the Whole Archive | Anton Nekrutenko (Penn State) |
| `astmh-hyphaeon-slides.html` | Evolutionary Questions at Archive Scale | Sergei L. Kosakovsky Pond (Temple University) |
| `astmh-ai-tools-slides.html` | Verifiable AI for Pathogen Genomics | Danielle Callan (Temple University) |
| `astmh-gtn-ai-slides.html` | Human-Written, Agent-Readable | Scott Cain (Galaxy Project) |

`index.html` is the landing page listing the talks.

## Deck conventions

- Built with [Reveal.js](https://revealjs.com/) 5.1, loaded from CDN (internet required to view).
- Deck-local assets (logos, figures, QR codes) are plain files referenced by relative path — keep them in the repo root alongside the HTML.
- Press `S` for speaker notes, `Esc` for slide overview, `F` for fullscreen.
- Append `?print-pdf` to a deck URL, then print → save as PDF, to export slides for sharing.

## Publishing

GitHub Pages: push to GitHub, then **Settings → Pages → Deploy from branch → `main` / root**.
`.nojekyll` is included so files are served as-is.
