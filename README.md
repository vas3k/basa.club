# Vas3k Base

Django app with server-rendered templates. Dynamic widgets are small React components ("islands") built by Vite from `frontend/`.

## Running locally without Docker

Requirements: Python 3.14 + [uv](https://docs.astral.sh/uv/), Node 24+, PostgreSQL, Redis.

```bash
uv sync
cd frontend && npm install && cd ..
uv run python manage.py migrate
```

Then run Django, the queue worker, and Vite:

```bash
# terminal 1
uv run python manage.py runserver
```

```bash
# terminal 2
uv run python manage.py qcluster
```

```bash
# terminal 3
cd frontend && npm run dev
```

Open http://127.0.0.1:8000. With `DEBUG` on (the default), Django loads JS directly from the Vite dev server on http://localhost:5173, so changes in `frontend/src/` show up instantly with hot reload. No rebuild is needed.

If Vite isn't running in this mode, pages still render but all React widgets are missing.

### Running with the production bundle

To check the built bundle instead of the dev server:

```bash
cd frontend && npm run build && cd ..
VITE_DEV_MODE=false uv run python manage.py runserver
```

`npm run build` writes the bundle and `manifest.json` to `frontend/dist/`, which Django serves as `/static/dist/`. Without `npm run dev`, nothing watches for changes, so rebuild after every edit.

## Running locally with Docker

```bash
docker compose up
```

This starts `postgres`, `redis`, `app` (Django on :8000), `queue` (django-q2 worker), `bot`, and `frontend` (Vite dev server on :5173 with hot reload). The `frontend/` folder is mounted into the container, so editing files locally updates the page in the browser.

The production image is built by the `Dockerfile`: a Node stage runs `npm run build`, and the result is copied into the Python image under `frontend/dist`. Run it with `DEBUG=false` (or `VITE_DEV_MODE=false`).

## Templates

Items have separate templates per page type, so future item types can get their own look:

```
templates/items/
  list/default.html     # item card in listings (included in a loop)
  show/layout.html      # item page shell: title, messages, comments
  show/default.html     # extends show/layout.html, fills {% block item %}
  compose/layout.html   # create/edit form shell: <form>, csrf, submit buttons
  compose/default.html  # extends compose/layout.html, fills {% block fields %}
  widgets/              # small pieces shared by list and show (tags, badges, manage)
templates/users/widgets/user_small.html   # avatar + name + reputation, reuse everywhere
```

`default.html` is the only variant for now. To add a type, create e.g. `show/event.html` that extends the same layout.

## Ratings

Rating is not the same as upvotes. Upvotes are a plain counter of clicks, while rating is calculated from votes and comment vibes. Users, items and comments each have their own rating.

All rules live in the `counters` app. Views persist the action, then call a matching function (`counters.item_upvoted`, `counters.comment_created`, …). Models and forms never touch ratings or counters. User rating changes are stored in the `ratings` table and shown at `/user/<slug>/ratings/`.

| Action | Comment author | Item | Comment | Item author |
|--------|----------------|------|---------|-------------|
| Upvote an item | | +1 | | +1 |
| Retract an item upvote | | -1 | | -1 |
| Top-level comment with a "good" vibe | +5 | +5 | | |
| Top-level comment with a "bad" vibe | -5 | -5 | | |
| Neutral comment or reply | | | | |
| «Полезно» on any comment | +1 | | +1 | |
| «Полезно» on a "good" vibe comment | +1 | +1 | +1 | |
| «Полезно» on a "bad" vibe comment | +1 | -1 | +1 | |
| Retract «Полезно» | -1 | -1 / +1 for "good" / "bad" vibe | -1 | |
Comments on your own item (and upvotes on those comments) do not change anyone's rating. Deleting a comment does not change ratings; run `recalculate_counters` if they drift.

Ratings are stored as integers and displayed divided by 10 with the `rating` template filter (`{{ user.rating|rating }}` shows 15 as +1.5 and -7 as -0.7). Items and top-level comments show their rating under the upvote button via `templates/common/widgets/rating.html`: green if positive, red if negative, hidden if zero.

To rebuild live ratings and counters from scratch (after changing the rules, or if they drift). This never touches the `ratings` history table:

```bash
uv run python manage.py recalculate_counters
```

## Frontend

All JS lives in `frontend/` and is bundled by Vite. Django renders the pages and owns forms, validation, and redirects. JS only makes parts of a page dynamic, in one of two ways:

- **Behavior**: plain TypeScript that adds interactivity to HTML Django already rendered, such as toggling the sidebar or making selects navigate. No React.
- **Island**: a React component that renders a widget itself, such as pickers or the markdown editor.

When choosing between them: if the markup comes from Django and you only need event handlers, write a behavior. If the widget has its own state and renders its own UI, write an island.

```
frontend/src/
  main.ts           # entry point: attaches behaviors, mounts islands
  core/             # runtime: behaviors.ts and islands.ts registries (rarely touched)
  behaviors/*.ts    # one file = one behavior, name = file name (kebab-case)
  islands/*.tsx     # one file = one island, name = file name (PascalCase)
  components/       # shared React components used by several islands
  lib/              # shared plain TS helpers (cookies, fetch, formatting)
  types.ts          # shared types
```

### Behaviors

Attach one or more behaviors with a space-separated `data-behavior` attribute. The element is passed to the behavior's default export:

```django
<form class="subheader-search" data-behavior="geo-select">...</form>
```

```ts
// frontend/src/behaviors/geo-select.ts
export default function geoSelect(form: HTMLElement) { ... }
```

Behaviors are bundled into `main.js` and run on every page that has a matching attribute, so keep them small.

### Islands

Mount an island from any template using the `island` tag (available everywhere, no `{% load %}` needed):

```django
{% island "MarkdownEditor" name="description" value=form.description.value|default:"" %}
```

Keyword arguments become React props, so they must be JSON-serializable. Names are converted to camelCase (`upvote_url=...` becomes `upvoteUrl`). If props need Python logic (permissions, URLs), wrap the island in a template tag, like `{% item_upvote item %}` in `items/templatetags/listing.py`. Inside a `<form>`, an island renders regular inputs with proper `name` attributes, so a normal form POST submits them.

Islands are code-split: React and each island's code load only on pages that use them, so heavy islands (like the markdown editor) don't slow down other pages.

To add a new widget, create `frontend/src/islands/MyWidget.tsx` with a default export and use `{% island "MyWidget" ... %}`. When an island grows, move its parts into `components/` (if shared) or into a folder next to it, like `islands/MyWidget/Toolbar.tsx`. Only `islands/*.tsx` files are registered as islands.

Useful commands (run in `frontend/`):

- `npm run dev`: dev server with hot reload
- `npm run build`: type-check and build the production bundle into `frontend/dist/`
- `npm run typecheck`: TypeScript check only

### Settings

Environment variables:

- `VITE_DEV_MODE` (`true`/`false`, defaults to the `DEBUG` value): load JS from the Vite dev server instead of `frontend/dist`
- `VITE_DEV_SERVER_HOST`, `VITE_DEV_SERVER_PORT` (defaults `localhost`, `5173`): where the browser finds the Vite dev server
