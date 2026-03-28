const ACTIVITY_LEVELS = [
  { value: 'sedentary', label: 'Sedentary' },
  { value: 'light',     label: 'Light' },
  { value: 'moderate',  label: 'Moderate' },
  { value: 'active',    label: 'Active' },
  { value: 'athlete',   label: 'Athlete' },
]

export default function ProfileForm({ profile, onChange }) {
  const set = (field) => (e) => onChange({ ...profile, [field]: e.target.value })

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 space-y-4">
      <h2 className="font-semibold text-gray-900">Your Profile</h2>
      <p className="text-xs text-gray-500 -mt-2">
        Used to personalize calorie targets. All fields optional.
      </p>

      {/* Age + Sex row */}
      <div className="flex gap-3">
        <div className="flex-1">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5 block">
            Age
          </label>
          <input
            type="number"
            min="10"
            max="100"
            placeholder="e.g. 20"
            value={profile.age}
            onChange={set('age')}
            className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm
                       bg-white text-gray-800 focus:outline-none focus:ring-2
                       focus:ring-ucla-blue focus:border-transparent"
          />
        </div>

        <div className="flex-1">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5 block">
            Sex
          </label>
          <div className="flex rounded-lg border border-gray-200 overflow-hidden">
            {['male', 'female'].map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => onChange({ ...profile, sex: s })}
                className={`flex-1 py-2.5 text-sm font-medium transition-colors capitalize
                  ${profile.sex === s
                    ? 'bg-ucla-blue text-white'
                    : 'bg-white text-gray-600 hover:bg-gray-50'}`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Weight + Height row */}
      <div className="flex gap-3">
        <div className="flex-1">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5 block">
            Weight (lbs)
          </label>
          <input
            type="number"
            min="50"
            max="500"
            placeholder="e.g. 155"
            value={profile.weightLbs}
            onChange={set('weightLbs')}
            className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm
                       bg-white text-gray-800 focus:outline-none focus:ring-2
                       focus:ring-ucla-blue focus:border-transparent"
          />
        </div>

        <div className="flex-1">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5 block">
            Height
          </label>
          <div className="flex gap-1.5">
            <input
              type="number"
              min="3"
              max="8"
              placeholder="ft"
              value={profile.heightFt}
              onChange={set('heightFt')}
              className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm
                         bg-white text-gray-800 focus:outline-none focus:ring-2
                         focus:ring-ucla-blue focus:border-transparent"
            />
            <input
              type="number"
              min="0"
              max="11"
              placeholder="in"
              value={profile.heightIn}
              onChange={set('heightIn')}
              className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm
                         bg-white text-gray-800 focus:outline-none focus:ring-2
                         focus:ring-ucla-blue focus:border-transparent"
            />
          </div>
        </div>
      </div>

      {/* Activity level */}
      <div>
        <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-1.5 block">
          Activity Level
        </label>
        <div className="flex gap-1.5 flex-wrap">
          {ACTIVITY_LEVELS.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              onClick={() => onChange({ ...profile, activity: value })}
              className={`px-3 py-2 rounded-full text-xs font-medium transition-colors
                ${profile.activity === value
                  ? 'bg-ucla-blue text-white shadow-sm'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
