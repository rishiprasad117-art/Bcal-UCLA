const DIETS = [
  { value: 'none', label: 'None' },
  { value: 'vegetarian', label: 'Vegetarian' },
  { value: 'vegan', label: 'Vegan' },
  { value: 'halal', label: 'Halal' },
]

const GOALS = [
  { value: 'cut', label: 'Cut' },
  { value: 'bulk', label: 'Bulk' },
  { value: 'maintain', label: 'Maintain' },
  { value: 'high_protein', label: 'High Protein' },
  { value: 'balanced', label: 'Balanced' },
]

const ALLERGENS = ['gluten', 'dairy', 'nuts', 'shellfish', 'soy']

export default function PreferencesForm({ prefs, onChange }) {
  const set = (key, value) => onChange((prev) => ({ ...prev, [key]: value }))

  const toggleAllergen = (allergen) => {
    set(
      'allergies',
      prefs.allergies.includes(allergen)
        ? prefs.allergies.filter((a) => a !== allergen)
        : [...prefs.allergies, allergen]
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-5">
      <h2 className="font-semibold text-gray-900">Your Preferences</h2>

      {/* Dietary restriction */}
      <div>
        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
          Dietary Restriction
        </label>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {DIETS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => set('diet', value)}
              className={`py-2 px-3 rounded-lg text-sm font-medium border transition-colors ${
                prefs.diet === value
                  ? 'bg-ucla-blue text-white border-ucla-blue'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-ucla-blue hover:text-ucla-blue'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Fitness goal */}
      <div>
        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
          Fitness Goal
        </label>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5">
          {GOALS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => set('goal', value)}
              className={`py-2 px-2 rounded-lg text-xs font-medium border transition-colors ${
                prefs.goal === value
                  ? 'bg-ucla-gold text-gray-900 border-ucla-gold'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-ucla-gold'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Allergies */}
      <div>
        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
          Allergies
        </label>
        <div className="flex flex-wrap gap-2">
          {ALLERGENS.map((allergen) => {
            const active = prefs.allergies.includes(allergen)
            return (
              <button
                key={allergen}
                onClick={() => toggleAllergen(allergen)}
                className={`px-3.5 py-1.5 rounded-full text-sm font-medium border transition-colors capitalize ${
                  active
                    ? 'bg-red-500 text-white border-red-500'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-red-300 hover:text-red-500'
                }`}
              >
                {allergen}
              </button>
            )
          })}
        </div>
      </div>

      {/* Likes / Dislikes */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5 block">
            Foods I like
          </label>
          <input
            type="text"
            placeholder="chicken, rice, broccoli…"
            value={prefs.likes}
            onChange={(e) => set('likes', e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm
                       placeholder-gray-300
                       focus:outline-none focus:ring-2 focus:ring-ucla-blue focus:border-transparent"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5 block">
            Foods to avoid
          </label>
          <input
            type="text"
            placeholder="mushrooms, spicy food…"
            value={prefs.dislikes}
            onChange={(e) => set('dislikes', e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm
                       placeholder-gray-300
                       focus:outline-none focus:ring-2 focus:ring-ucla-blue focus:border-transparent"
          />
        </div>
      </div>
    </div>
  )
}
