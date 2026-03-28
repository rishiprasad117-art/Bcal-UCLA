export default function LocationMealPicker({
  locations,
  loading,
  selectedLocation,
  selectedMeal,
  onLocationChange,
  onMealChange,
}) {
  const meals = selectedLocation
    ? selectedLocation.available_meals
    : []

  const handleSelect = (e) => {
    const loc = locations.find((l) => l.location_id === e.target.value)
    if (loc) onLocationChange(loc)
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
      <h2 className="font-semibold text-gray-900">Where are you eating?</h2>

      {/* Location dropdown */}
      <div>
        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5 block">
          Dining Hall
        </label>
        <select
          value={selectedLocation?.location_id ?? ''}
          onChange={handleSelect}
          disabled={loading}
          className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm
                     bg-white text-gray-800
                     focus:outline-none focus:ring-2 focus:ring-ucla-blue focus:border-transparent
                     disabled:text-gray-400 disabled:bg-gray-50"
        >
          <option value="">{loading ? 'Loading locations…' : 'Select a location…'}</option>
          {locations.map((loc) => (
            <option key={loc.location_id} value={loc.location_id}>
              {loc.name}
            </option>
          ))}
        </select>
      </div>

      {/* Meal period pills */}
      {meals.length > 0 && (
        <div>
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5 block">
            Meal Period
          </label>
          <div className="flex gap-2 flex-wrap">
            {meals.map((meal) => (
              <button
                key={meal}
                onClick={() => onMealChange(meal)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                  selectedMeal === meal
                    ? 'bg-ucla-blue text-white shadow-sm'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {meal}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
