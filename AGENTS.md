# Basa contributor guidelines

These instructions apply throughout the repository. Basa (`basa.club`) is a Django
community listings website with PostgreSQL, server-rendered HTML, and isolated React
widgets. Favor readable code, familiar tools, and small changes over abstractions.
See `README.md` for environment setup and deployment configuration.

## Workflow and permissions

- Read the relevant code and `git status` before editing. Preserve unrelated and
  staged work; do not reset, reformat, or refactor it as part of another task.
- Do not commit, push, deploy, or apply database migrations without explicit user
  consent. Permission to edit code does not authorize these operations.
- Add or run tests only when explicitly requested. Builds, type checks, linters,
  and smoke checks also require an explicit request; commands below are reference,
  not instructions to execute them automatically.
- Review the diff and affected callers, templates, and configuration. Report what
  changed, which checks actually ran, and any remaining limitations.

## Commands and entry points

Run commands from the repository root. Local development must work without Docker;
keep the Docker development option as well.

| Task | Command |
| --- | --- |
| Install Python dependencies | `uv sync --frozen` |
| Install frontend dependencies | `npm ci --prefix frontend` |
| Run Django | `uv run python manage.py runserver` |
| Run Vite | `npm run dev --prefix frontend` |
| Run background workers | `uv run python manage.py qcluster` |
| Build frontend, including TypeScript checks | `npm run build --prefix frontend` |

Django settings read process environment variables; they do not automatically load
`.env`. Use the committed dependency lockfiles. Edit frontend source, not generated
files under `frontend/static/dist/`.

## Code conventions

- Use ordinary Django views, forms, models, queries, and template tags. Keep logic
  in the relevant domain app; do not introduce service/repository layers or generic
  frameworks for a local feature.
- Prefer small duplication to premature extraction. Do not create a helper used
  in fewer than three places **or** containing fewer than five meaningful lines.
  These thresholds are necessary, not sufficient: extraction must improve reading.
  Do not pad functions or invent callers to meet them.
- Do not introduce `_underscore`-prefixed helpers or disguise ordinary logic as
  protocol methods. Prefer conventional, descriptive names; protocol methods have
  no blanket exemption and should be used only for their actual language/framework
  purpose. Required views, callbacks, React components, and framework hooks are not
  utility helpers.
- Keep `__init__.py` files empty or minimal: necessary imports, singleton instances,
  and genuine package initialization only. Keep helpers and business logic in named
  modules. Use `__init__` methods only for actual object initialization, not as a
  home for unrelated work. Prefer conventionally named functions for explicit
  setup operations where possible, subject to the helper-extraction rule above.
- Separate logical groups with blank lines: input, validation, queries, mutation,
  response. Prefer explicit control flow over dense one-liners. Match surrounding
  indentation and formatting; avoid unrelated formatting changes.
- Make code self-documenting through clear names, explicit steps, and logical
  line breaks, even when this takes more lines. Comments are for human readers,
  not an agent's notes to itself. Add them only for genuinely tricky behavior,
  non-obvious constraints, or reasoning the code cannot express. Do not narrate
  each line, document every function, or add boilerplate docstrings and LLM filler.
- Reuse existing dependencies and patterns. Existing exceptions do not justify
  repeating them or launching a repository-wide cleanup.

## Dependencies and supply chain

- Use the standard library, browser APIs, Django, and existing packages first.
  Do not add an npm or Python package for a simple one-off function or convenience
  wrapper. A short local implementation is preferable for ordinary small tasks.
- A new dependency must solve a substantial need. Explain why existing tools are
  insufficient and review its maintenance, license, transitive dependencies, and
  install/build scripts before adding it. Use established libraries for complex
  security-sensitive work; do not invent cryptography to avoid a dependency.
- Verify the exact package name, registry entry, and upstream ownership through
  official sources. Check known security advisories and available provenance;
  downloads or a familiar-looking name alone are not evidence of trust.
- Keep changes to `pyproject.toml`/`uv.lock` or
  `frontend/package.json`/`frontend/package-lock.json` consistent and scoped.
  Preserve frozen installs; do not regenerate locks or upgrade unrelated packages.
- Do not run unreviewed remote installers, unpinned `npx`/`uvx` tools, or arbitrary
  Git/URL dependencies. Never bypass integrity checks or expose credentials to
  package scripts to make an installation succeed.

## File locations: mandatory

All paths below are relative to the repository root. These are required locations,
not suggestions; do not create alternative asset or template directories.

| Content | Required location |
| --- | --- |
| Images, icons, logos, favicons | `frontend/static/images/` |
| Font files | `frontend/static/fonts/` |
| Stylesheets | `frontend/static/css/` |
| Authored JavaScript/TypeScript and React | `frontend/src/` |
| Generated Vite bundles | `frontend/static/dist/` (build output only) |
| All project-owned Django templates | `templates/` with feature subdirectories |

Keep shared layouts/widgets in the existing template structure and admin templates
under `templates/godmode/`. Do not put templates or static assets inside Django
apps, add `public/` or a parallel `assets/` tree, or colocate CSS/images with React
components. Do not change template/static discovery to accommodate a misplaced file.
Use Django's static tag for asset URLs. `STATIC_ROOT` is collection output, never
an authoring directory. User uploads belong to the media service, not static assets.

## Django and data

Django owns page content, routing, permissions, validation, and forms. Preserve
ordinary links, GET filters, POST submissions, redirects, and server-side pagination.
Keep authorization, CSRF protection, visibility rules, and soft-delete behavior on
all relevant paths; browser state is never an authorization check.

Use existing domain apps and template widgets. Include migrations with schema
changes and account for existing data, queries, forms, and background jobs.
**Every model or database change also requires the Godmode review below.**
Keep credentials out of source, images, frontend props, and logs.

## Frontend: Django pages with React islands

**Never turn this website into an SPA.** React handles interaction, not page
content. Do not add client-side routing, a global React root/store, or React
replacements for Django-rendered listings, profiles, layouts, or navigation.

Prefer native HTML first. A short inline JavaScript handler is appropriate for a
simple local interaction. Use a TypeScript behavior to enhance existing markup;
use a React island only for a widget that needs meaningful interactive state,
such as an editor, picker, upload control, or voting button.

- `frontend/src/main.ts` attaches behaviors and mounts islands. Files in
  `frontend/src/behaviors/` enhance elements marked with `data-behavior`.
- `{% island "WidgetName" ... %}` in a Django template emits a mount point and
  serialized props through `common/templatetags/islands.py`. Prop names become
  camelCase. The runtime lazily loads React and the default export from
  `frontend/src/islands/WidgetName.tsx` only where needed.
- Keep state and DOM ownership inside the widget. Pass initial data and URLs from
  Django. Form widgets expose named inputs for ordinary Django form submissions.
- Reuse `frontend/src/lib/http.ts` for asynchronous JSON actions and CSRF handling.
  Use safe serialization for JavaScript data; never interpolate untrusted values
  into executable inline JavaScript or bypass template escaping.

## Design and CSS

Existing templates and `frontend/static/css/` are the design library. Reuse shared
widgets, classes, theme variables, typography, spacing, and responsive patterns.
Read `theme.css`, `base.css`, and the relevant page stylesheet before adding styles;
account for `mobile.css` when changing layout. React uses the same CSS as Django.

Unify repeated visual patterns in existing stylesheets. Do not add a UI kit, CSS
framework, parallel component system, or a generic generated redesign. Preserve
the site's visual language rather than introducing decorative cards, gradients,
or dashboard layouts unrelated to the requested feature. Use plain, specific copy.

## Godmode: custom administration

Godmode is the project's custom admin and moderation interface:

- `godmode/config.py`: model registrations, columns, editable/hidden fields, actions.
- `godmode/admin.py`: model-driven forms, display, and access rules.
- `godmode/views/`, `godmode/actions/`: request handling and administrative actions.
- `templates/godmode/`, `frontend/static/css/godmode.css`: admin UI and styling.

For every model or database change, inspect affected admin registrations, field
names, list/create/edit forms, ordering/filtering, relation widgets, and actions.
Update affected configuration and templates in the same change. Generated forms
can expose new fields: explicitly check sensitive fields and privilege changes.
Preserve staff/superuser boundaries, including superuser-only user creation/editing.
A migration alone does not establish admin compatibility. Review by reading code;
execute checks only within the permissions above.

## Production architecture

Production uses Docker Compose over SSH on the existing host, following the
`vas3k.club` deployment pattern. Reuse host nginx and PostgreSQL. Keep the workflow
in `.github/workflows/deploy.yml` short: build/publish, prepare `.env`, copy it and
Compose, then run Compose. The Dockerfile builds frontend assets; `Makefile` handles
web startup, migrations, static collection, and Gunicorn.

Keep this architecture simple: no Kubernetes, microservices, custom release
framework, deployment-script hierarchy, or separate production settings module.
Update the README when changing setup or operational commands. Keep this file
focused on durable, actionable rules; do not accumulate task history or duplicate
implementation details that belong in code.
