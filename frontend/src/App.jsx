import { useState, useEffect, useRef } from 'react'
import LocationMealPicker from './components/LocationMealPicker'
import PreferencesForm from './components/PreferencesForm'
import ProfileForm from './components/ProfileForm'
import ResultsView from './components/ResultsView'

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:5000'

const WORKOUT_DAYS_TO_ACTIVITY = {
  '0':         'sedentary',
  '1-2':       'light',
  '3-4':       'moderate',
  '5-6':       'active',
  'every-day': 'athlete',
}

const DEFAULT_PROFILE = {
  age: '',
  sex: 'male',
  weightLbs: '',
  heightFt: '',
  heightIn: '',
  workoutDays: '3-4',
}

const DEFAULT_PREFS = {
  diet: 'none',
  goal: 'balanced',
  allergies: [],
  likes: '',
  dislikes: '',
}

export default function App() {
  const [locations, setLocations] = useState([])
  const [locationsLoading, setLocationsLoading] = useState(true)
  const [locationsError, setLocationsError] = useState(false)

  const [profile, setProfile] = useState(DEFAULT_PROFILE)

  const [selectedLocation, setSelectedLocation] = useState(null)
  const [selectedMeal, setSelectedMeal] = useState(null)
  const [prefs, setPrefs] = useState(DEFAULT_PREFS)

  const [results, setResults] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState(null)

  const resultsRef = useRef(null)

  // Load locations on mount
  useEffect(() => {
    fetch(`${API_BASE}/locations`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then((data) => {
        setLocations(data)
        setLocationsLoading(false)
      })
      .catch(() => {
        setLocationsError(true)
        setLocationsLoading(false)
      })
  }, [])

  const handleLocationChange = (location) => {
    setSelectedLocation(location)
    const meals = location.available_meals
    setSelectedMeal(meals[0])
    setResults(null)
    setSubmitError(null)
  }

  const handleMealChange = (meal) => {
    setSelectedMeal(meal)
    setResults(null)
    setSubmitError(null)
  }

  const handleSubmit = async () => {
    if (!selectedLocation || !selectedMeal) return

    setSubmitting(true)
    setSubmitError(null)

    const body = {
      location_id: selectedLocation.location_id,
      meal: selectedMeal,
      goal: prefs.goal,
      diet: prefs.diet,
      allergies: prefs.allergies,
      likes: prefs.likes
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      dislikes: prefs.dislikes
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean),
      top_n: 10,
      // Physical profile (all optional — omitted if blank)
      ...(profile.age       && { age:        Number(profile.age) }),
      ...(profile.weightLbs && { weight_lbs: Number(profile.weightLbs) }),
      ...(profile.heightFt  && { height_ft:  Number(profile.heightFt),
                                  height_in:  Number(profile.heightIn) || 0 }),
      sex:      profile.sex,
      activity: WORKOUT_DAYS_TO_ACTIVITY[profile.workoutDays] ?? 'moderate',
    }

    try {
      const res = await fetch(`${API_BASE}/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.error ?? `Server error ${res.status}`)
      }

      const data = await res.json()
      setResults(data)

      // Scroll results into view on mobile
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth' }), 50)
    } catch (err) {
      setSubmitError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const canSubmit = selectedLocation && selectedMeal && !submitting

  return (
    <div className="min-h-screen bg-gray-50">
      {/* ── Header ── */}
      <header className="bg-ucla-blue text-white sticky top-0 z-10 shadow-sm">
        <div className="max-w-2xl mx-auto px-4 py-3.5 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold tracking-tight leading-none">BCal</h1>
            <p className="text-ucla-blue-light text-xs mt-0.5">UCLA Smart Nutrition Planner</p>
          </div>
          {/* Gold circle logo mark */}
          <div className="w-9 h-9 rounded-full bg-ucla-gold flex items-center justify-center shadow">
            <span className="text-ucla-blue-dark font-extrabold text-base leading-none">B</span>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-5 space-y-4 pb-16">
        {/* ── API unreachable error ── */}
        {locationsError && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4">
            <p className="text-red-700 text-sm font-medium">Flask backend is not running.</p>
            <p className="text-red-600 text-sm mt-1">
              Start it with{' '}
              <code className="bg-red-100 px-1.5 py-0.5 rounded text-xs font-mono">
                python api.py
              </code>{' '}
              then refresh this page.
            </p>
          </div>
        )}

        {/* ── Step 0: Personal profile ── */}
        <ProfileForm profile={profile} onChange={setProfile} />

        {/* ── Step 1: Location + Meal ── */}
        <LocationMealPicker
          locations={locations}
          loading={locationsLoading}
          selectedLocation={selectedLocation}
          selectedMeal={selectedMeal}
          onLocationChange={handleLocationChange}
          onMealChange={handleMealChange}
        />

        {/* ── Step 2: Preferences (only shown after location selected) ── */}
        {selectedLocation && (
          <PreferencesForm prefs={prefs} onChange={setPrefs} />
        )}

        {/* ── Submit button ── */}
        {selectedLocation && selectedMeal && (
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className="w-full bg-ucla-blue text-white font-semibold py-3.5 rounded-xl
                       shadow-sm hover:bg-ucla-blue-dark active:scale-[0.98]
                       transition-all duration-150
                       disabled:opacity-60 disabled:cursor-not-allowed
                       flex items-center justify-center gap-2"
          >
            {submitting ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Finding recommendations…
              </>
            ) : (
              'Get Recommendations'
            )}
          </button>
        )}

        {/* ── Submit error ── */}
        {submitError && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
            <span className="font-medium">Error: </span>
            {submitError}
          </div>
        )}

        {/* ── Results ── */}
        <div ref={resultsRef}>
          {results && !submitting && <ResultsView results={results} />}
        </div>
      </main>
    </div>
  )
}
