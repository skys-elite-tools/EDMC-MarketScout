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

export function ly(v) {
  const n = num(v)
  if (n === null) return '—'
  if (Math.abs(n) < 0.005) return '0'
  const digits = n < 10 ? 2 : 1
  return n.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: 0 })
}

export const POTENTIAL_PROFIT_LOW_MAX = 20000
export const POTENTIAL_PROFIT_MEDIUM_MAX = 35000
export const POTENTIAL_PROFIT_DISPLAY_THRESHOLD = 10000

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

export function compactDateTime(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  const date = d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: '2-digit' })
  const time = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  return `${date}, ${time}`
}

export function rareDateTime(v) {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return String(v)
  const month = d.toLocaleString(undefined, { month: 'short' }).replace(/\.$/, '')
  const day = String(d.getDate()).padStart(2, '0')
  const time = d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', hour12: false })
  return `${month}.${day} ${time}`
}

export function query(params) {
  return new URLSearchParams(params).toString()
}

export function columnKey(col) {
  return `${col.commodity}::${col.side}`
}

export function inaraCommoditySellUrl(system, inaraId) {
  const id = num(inaraId)
  const nearSystem = String(system || '').trim()
  if (id === null || id <= 0 || !nearSystem) return ''
  const params = new URLSearchParams()
  params.set('formbrief', '1')
  params.set('pi1', '2')
  params.append('pa1[]', String(Math.trunc(id)))
  params.set('ps1', nearSystem)
  params.set('pi10', '1')
  params.set('pi11', '0')
  params.set('pi3', '3')
  params.set('pi9', '0')
  params.set('pi4', '0')
  params.set('pi8', '1')
  params.set('pi13', '1')
  params.set('pi5', '0')
  params.set('pi12', '0')
  params.set('pi7', '0')
  params.set('pi14', '0')
  params.set('ps3', '')
  return `https://inara.cz/elite/commodities/?${params.toString()}`
}

export function potentialProfitTooltip(maxSell) {
  const maxSellText = money(maxSell)
  if (maxSellText === '—') return 'Search current sell prices on Inara.'
  return `Search current sell prices on Inara. Theoretical max uses max sell: ${maxSellText} Cr/t.`
}

export function commodityCellParts(row, commodity, side) {
  const qtyName = side === 'buy' ? 'supply' : 'demand'
  const qtyValue = row[`${commodity}_${qtyName}`]
  const priceValue = row[`${commodity}_${side}`]
  const hideZeroBuy = side === 'buy' && num(priceValue) === 0
  const potentialProfit = side === 'buy' ? row[`${commodity}_potential_profit`] : null
  return {
    price: hideZeroBuy ? '—' : money(priceValue),
    qtyName,
    qty: money(qtyValue),
    qtyClass: quantityClass(qtyValue),
    showQuantity: !hideZeroBuy,
    potentialProfit: money(potentialProfit),
    potentialProfitClass: potentialProfitClass(potentialProfit),
    hasPotentialProfit: !hideZeroBuy && shouldDisplayPotentialProfit(potentialProfit),
    inaraId: row[`${commodity}_inara_id`],
    maxSell: row[`${commodity}_max_sell`],
  }
}

export function quantityClass(value) {
  const n = num(value)
  if (n === null) return ''
  if (n === 0) return 'quantityHigh'
  if (n <= 7000) return 'quantityLow'
  if (n <= 15000) return 'quantityMedium'
  return 'quantityHigh'
}

export function potentialProfitClass(value) {
  const n = num(value)
  if (n === null) return ''
  if (n <= POTENTIAL_PROFIT_LOW_MAX) return 'potentialLow'
  if (n <= POTENTIAL_PROFIT_MEDIUM_MAX) return 'potentialMedium'
  return 'potentialHigh'
}

export function shouldDisplayPotentialProfit(value) {
  const n = num(value)
  return n !== null && n >= POTENTIAL_PROFIT_DISPLAY_THRESHOLD
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
