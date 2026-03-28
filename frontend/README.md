# BCal Frontend

React + Vite + Tailwind CSS frontend for the BCal UCLA Nutrition Planner.

## Quick start

**Prerequisites:** Node 18+ and the Flask backend running.

```bash
# 1. Install dependencies
cd frontend
npm install

# 2. Start Flask backend (in a separate terminal)
cd ..
python api.py          # starts at http://localhost:5000

# 3. Start the dev server
npm run dev            # starts at http://localhost:5173
```

Open http://localhost:5173. Vite proxies all `/api/*` requests to `http://localhost:5000`
so there are no CORS issues during development.

## How the API proxy works

`vite.config.js` maps `/api/*` → `http://localhost:5000/*` at the dev server level.
The app calls `/api/locations`, `/api/recommend`, etc., and Vite rewrites and
forwards them to Flask transparently.

If you need to point at a Flask instance on a different host/port, set the
`VITE_API_BASE` environment variable before starting:

```bash
VITE_API_BASE=http://192.168.1.10:5000 npm run dev
```

## Build for production

```bash
npm run build      # outputs to frontend/dist/
npm run preview    # serve the production build locally
```

For production deployment you have two options:

1. **Serve from Flask** — copy `dist/` into Flask's static folder and add a
   catch-all route that serves `index.html`. No CORS needed.

2. **Separate hosts** — install `flask-cors` and add `CORS(app)` to `api.py`,
   then set `VITE_API_BASE` at build time to the Flask origin.

## Project structure

```
frontend/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── src/
    ├── main.jsx
    ├── index.css
    ├── App.jsx                       # root state + layout
    └── components/
        ├── LocationMealPicker.jsx    # location dropdown + meal pills
        ├── PreferencesForm.jsx       # diet / goal / allergies / likes
        ├── RecommendationCard.jsx    # single food item card
        └── ResultsView.jsx           # results list + filtered section
```

## Design

- **Colors:** UCLA Blue `#2774AE` and Gold `#FFD100` as the accent palette
- **Layout:** single-column, `max-w-2xl` centered, works on iPhone and desktop
- **No external UI libraries** — Tailwind CSS only
