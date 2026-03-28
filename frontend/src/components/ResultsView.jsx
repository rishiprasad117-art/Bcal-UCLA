import { useState } from 'react'
import RecommendationCard from './RecommendationCard'

const GOAL_LABELS = {
  cut: 'Cut',
  bulk: 'Bulk',
  maintain: 'Maintain',
  high_protein: 'High Protein',
  balanced: 'Balanced',
}

export default function ResultsView({ results }) {
  const [showFiltered, setShowFiltered] = useState(false)

  const recs = results.recommendations ?? []
  const filtered = results.filtered_out ?? []
  const goalLabel = GOAL_LABELS[results.goal] ?? results.goal

  const targets = results.targets

  return (
    <div className="space-y-4">

      {/* ── Calorie & macro targets (shown when physical profile was provided) ── */}
      {targets && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
          <p className="text-xs font-medium text-blue-600 uppercase tracking-wide mb-2">
            Your Daily Targets
          </p>
          <div className="flex gap-4 flex-wrap">
            <div className="text-center">
              <p className="text-lg font-bold text-blue-800">{targets.target_cal}</p>
              <p className="text-xs text-blue-600">kcal</p>
            </div>
            <div className="w-px bg-blue-200" />
            <div className="text-center">
              <p className="text-lg font-bold text-blue-800">{targets.protein_g}g</p>
              <p className="text-xs text-blue-600">protein</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-blue-800">{targets.carbs_g}g</p>
              <p className="text-xs text-blue-600">carbs</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-blue-800">{targets.fat_g}g</p>
              <p className="text-xs text-blue-600">fat</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Summary header ── */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2 className="text-base font-semibold text-gray-900">
            {recs.length > 0
              ? `${recs.length} Recommendation${recs.length !== 1 ? 's' : ''}`
              : 'No Recommendations'}
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            {results.location} · {results.meal} · {goalLabel} goal
          </p>
        </div>
        <span className="text-xs text-gray-400 flex-shrink-0 mt-1">{results.date}</span>
      </div>

      {/* ── Empty state ── */}
      {recs.length === 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center space-y-1">
          <p className="text-amber-700 font-medium text-sm">
            No items match your current filters
          </p>
          <p className="text-amber-600 text-xs">
            Try relaxing your dietary restriction, removing allergens, or choosing a different meal
          </p>
        </div>
      )}

      {/* ── Recommendation cards ── */}
      {recs.length > 0 && (
        <div className="space-y-3">
          {recs.map((item, i) => (
            <RecommendationCard key={`${item.item}-${i}`} item={item} rank={i + 1} />
          ))}
        </div>
      )}

      {/* ── Filtered out (collapsible) ── */}
      {filtered.length > 0 && (
        <div className="rounded-xl border border-gray-200 overflow-hidden">
          <button
            onClick={() => setShowFiltered((v) => !v)}
            className="w-full flex items-center justify-between px-4 py-3
                       bg-gray-50 hover:bg-gray-100 transition-colors text-left"
          >
            <span className="text-sm text-gray-600 font-medium">
              {filtered.length} item{filtered.length !== 1 ? 's' : ''} filtered out
            </span>
            <span className="text-gray-400 text-xs font-medium ml-2">
              {showFiltered ? '▲ Hide' : '▼ Show'}
            </span>
          </button>

          {showFiltered && (
            <ul className="divide-y divide-gray-100">
              {filtered.map((item, i) => (
                <li
                  key={i}
                  className="flex items-center justify-between gap-3 px-4 py-2.5"
                >
                  <span className="text-sm text-gray-600 min-w-0 truncate">{item.item}</span>
                  <span className="flex-shrink-0 text-xs text-red-500 bg-red-50 px-2 py-0.5 rounded-full">
                    {item.reason}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
