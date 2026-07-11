export function fmt(v) {
  return v === null || v === undefined || v === '' ? '—' : String(v)
}

export function num(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

export function money(v) {
  const n = num(v)
  return n === null ? '—' : Math.round(n).toLocaleString()
}

export function shortTime(v) {
  if (!v) return '—'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleTimeString()
}

export function localDateTime(v) {
  if (!v) return '—'
  const d = new Date(v)
  return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString()
}

export function query(params) {
  return new URLSearchParams(params).toString()
}

export function columnKey(col) {
  return `${col.commodity}::${col.side}`
}

export function commodityCellParts(row, commodity, side) {
  const qtyName = side === 'buy' ? 'supply' : 'demand'
  return {
    price: money(row[`${commodity}_${side}`]),
    qtyName,
    qty: money(row[`${commodity}_${qtyName}`]),
  }
}

export function stationDedupeKey(row) {
  const system = String(row.system || '').trim().toLowerCase()
  const station = String(row.station || '').trim().toLowerCase()
  return `${system}|${station}`
}

function rowDateScore(v) {
  if (!v) return 0
  const t = new Date(v).getTime()
  return Number.isFinite(t) ? t : 0
}

function rowQualityScore(row) {
  let score = 0
  if (row.station_visit) score += 1_000_000_000_000_000
  score += rowDateScore(row.market_updated)
  score += Math.max(0, Number(row.best_buy_score || 0))
  if (row.source === 'local_visit') score += 1_000_000
  return score
}

export function dedupeStationRows(inputRows) {
  const byKey = new Map()
  for (const row of inputRows || []) {
    const key = stationDedupeKey(row)
    if (!key || key === '|') continue
    const current = byKey.get(key)
    if (!current || rowQualityScore(row) > rowQualityScore(current)) {
      byKey.set(key, row)
    }
  }
  return Array.from(byKey.values())
}

export function rowFlag(row, watchedCommodities, priceThreshold, supplyThreshold) {
  const cheap = []
  const strong = []
  for (const commodity of watchedCommodities || []) {
    const buy = num(row[`${commodity}_buy`])
    const supply = num(row[`${commodity}_supply`])
    if (buy !== null && buy > 0 && buy <= priceThreshold) {
      cheap.push(commodity)
      if (supply !== null && supply >= supplyThreshold) strong.push(commodity)
    }
  }
  if (strong.length) return { cls: 'strong', marker: '★★', items: strong.slice(0, 3) }
  if (cheap.length) return { cls: 'cheap', marker: '★', items: cheap.slice(0, 3) }
  return { cls: '', marker: '', items: [] }
}
