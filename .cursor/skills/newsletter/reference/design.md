# Card Back: the design

```
CHOSEN_TEMPLATE: card-back
```

The owner picked **Card Back**, the only template: `newsletter/templates/card-back.html`, with its two fonts (Alfa Slab One, Archivo Narrow) in `newsletter/fonts/` and their licenses in `newsletter/fonts/licenses/`. It looks like the back of a vintage football card: card-stock background, maroon ink, rose cards, slab-serif names and numbers. Render every issue with it and don't restyle it per issue. The template is final. Design changes follow `.cursor/skills/frontend-design/SKILL.md` and need the owner's sign-off; the final checklist fails if the template or fonts differ from `main`.

## The owner's standing design notes

- Recap cards must let a manager find their own team fast while scrolling on a phone. Team names are the biggest type on each card, the winner always sits on top, and the section opens with the "Find your team" list that links to every card (`build.py` builds that list from `recaps`).
- No provenance paragraph, format line, or byline on the page, no intro lines under section headings, and no standalone NFL results section. The football goes inside the recaps, lead, awards, and standouts.
- Under the power rankings, render draws the Elo progression chart. See below. Do not have the writer invent a chart or describe one in copy.

## The Elo progression chart

`newsletter/elo.py` (`chart_html`) builds the chart at render time from `newsletter/elo/<season>.json` and `build.py` inserts it as `elo_chart` under the rankings list. The writer does not write this field.

- Inline SVG, `#elo-chart`, self-contained: no JS, no extra fonts, no CDNs.
- One monotone-cubic (Fritsch–Carlson) line per team, a point on every recorded week including week 0 at 1000.
- Week axis and Elo axis. The 1000 line is dashed ink (`#262321`), not maroon: maroon is a team color.
- Twelve Card Back inks, keyed by Sleeper `roster_id`. The legend is in Find-your-team name order. Each key is a short stroke and dot in the same color as that team's line, on the same rose card as the plot.
- Teams that share a rating sit on the same path. Do not nudge them apart. They split when the ratings do.
- Readable at 390px. The plot takes the full column; names live in the legend, not as end labels on the lines.

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
| `elo_chart` | `#elo-chart` is present, with 12 team lines, a point per recorded week, a 12-name legend, and each legend stroke equal to that team's line. |

It also saves `screenshots/phone-first-screen.png`, `phone-full.png`, `desktop-first-screen.png`, and `desktop-full.png` for the pull request.
