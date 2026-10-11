# Card Back: the design

```
CHOSEN_TEMPLATE: card-back
```

The owner picked **Card Back**, the only template: `newsletter/templates/card-back.html`, with its two fonts (Alfa Slab One, Archivo Narrow) in `newsletter/fonts/` and their licenses in `newsletter/fonts/licenses/`. It looks like the back of a vintage football card: card-stock background, maroon ink, rose cards, slab-serif names and numbers. Render every issue with it and don't restyle it per issue. The template is final. Design changes follow `.cursor/skills/frontend-design/SKILL.md` and need the owner's sign-off; the final checklist fails if the template or fonts differ from `main`.

## The owner's standing design notes

- Recap cards must let a manager find their own team fast while scrolling on a phone. Team names are the biggest type on each card, the winner always sits on top, and the section opens with the "Find your team" list that links to every card (`build.py` builds that list from `recaps`).
- No provenance paragraph, format line, or byline on the page, no intro lines under section headings, and no standalone NFL results section. The football goes inside the recaps, lead, awards, and standouts.
- Under the power rankings, an Elo-by-week line chart (`#elo-chart`) is generated in Python at render time as inline SVG: monotone-cubic curves, a point on each recorded week, twelve Card Back colors, a week axis and an Elo axis, end labels on desktop, and a legend in Find-your-team order (team names first). It must stay self-contained: no JS, no extra fonts, no CDNs.

## What the HTML gate checks

`python3 newsletter/run.py verify --week <N>` opens the rendered page in headless Chromium at 390px (phone) and 1280px (desktop) wide and checks:

| Check | Pass means |
| --- | --- |
| `no_horizontal_scroll` | The page is no wider than the screen. |
| `no_network_requests` | Nothing loads from the network; only `data:` URLs and the file itself. The page is one self-contained file. |
| `fonts_loaded` | All five embedded font faces load and both families are available. |
| `no_console_errors` | No console errors and no page errors. |
| `no_template_leftovers` | No unrendered `{{` anywhere in the page. |
| `find_your_team_links` | Twelve links, each landing on a recap card. |
| `elo_chart` | `#elo-chart` is present, with 12 team lines, a point per recorded week, and a 12-name legend. |

It also saves `screenshots/phone-first-screen.png`, `phone-full.png`, `desktop-first-screen.png`, and `desktop-full.png` for the pull request.
