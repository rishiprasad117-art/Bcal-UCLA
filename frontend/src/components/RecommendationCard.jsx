// Score badge: green for high, gold for mid, gray for low/zero
function ScoreBadge({ score }) {
  let cls
  if (score >= 8)      cls = 'bg-emerald-500 text-white'
  else if (score >= 4) cls = 'bg-ucla-gold text-gray-900'
  else                 cls = 'bg-gray-200 text-gray-600'

  return (
    <span className={`flex-shrink-0 px-2.5 py-1 rounded-full text-xs font-bold tabular-nums ${cls}`}>
      {score != null ? score.toFixed(1) : '—'}
    </span>
  )
}

// Small pill for section type
function SectionBadge({ sectionType }) {
  if (!sectionType || sectionType === 'static') return null
  const label = sectionType === 'rotating' ? 'rotating' : 'build your own'
  return (
    <span className="ml-1.5 px-1.5 py-0.5 bg-ucla-blue-light/20 text-ucla-blue text-xs rounded font-medium">
      {label}
    </span>
  )
}

export default function RecommendationCard({ item, rank }) {
  const missingNutrition = item.data_quality === 'missing'
  const cal = missingNutrition || item.calories === 0 ? null : item.calories
  const protein = missingNutrition || item.protein_grams === 0 ? null : item.protein_grams

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 space-y-3 active:bg-gray-50 transition-colors">

      {/* ── Row 1: rank + name + score ── */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          {/* Rank bubble */}
          <span className="flex-shrink-0 mt-0.5 w-6 h-6 rounded-full bg-ucla-blue text-white
                           text-xs font-bold flex items-center justify-center leading-none">
            {rank}
          </span>

          {/* Name + station */}
          <div className="min-w-0">
            <h3 className="font-semibold text-gray-900 leading-snug break-words">
              {item.item}
            </h3>
            <p className="text-xs text-gray-400 mt-0.5 flex items-center flex-wrap">
              {item.station}
              <SectionBadge sectionType={item.section_type} />
            </p>
          </div>
        </div>

        <ScoreBadge score={item.score} />
      </div>

      {/* ── Row 2: calories + protein ── */}
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-1">
          <span aria-hidden>🔥</span>
          <span className="font-semibold text-gray-800">
            {cal != null ? cal : '—'}
          </span>
          <span className="text-gray-400 text-xs">cal</span>
        </div>
        <div className="flex items-center gap-1">
          <span aria-hidden>💪</span>
          <span className="font-semibold text-gray-800">
            {protein != null ? `${protein}g` : '—'}
          </span>
          <span className="text-gray-400 text-xs">protein</span>
        </div>

        {/* Data quality note */}
        {item.data_note && (
          <span className="ml-auto text-xs text-amber-500 flex-shrink-0">
            ⚠ {item.data_quality === 'estimated' ? 'approx.' : 'no data'}
          </span>
        )}
      </div>

      {/* ── Row 3: reasons ── */}
      {item.reasons?.length > 0 && (
        <div className="border-t border-gray-100 pt-3 space-y-1.5">
          {item.reasons.map((reason, i) => (
            <p key={i} className="text-xs text-gray-500 flex items-start gap-1.5">
              <span className="text-emerald-500 mt-px flex-shrink-0 font-bold">✓</span>
              <span>{reason}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
