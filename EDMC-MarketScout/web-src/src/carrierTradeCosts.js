export const TRITIUM_PRICE_PER_TONNE = 70000
export const HULL_MAINTENANCE_PER_JUMP = 100000
export const TRADE_JUMP_COUNT = 2

export const CARRIER_TRITIUM_TONNES = {
  fleet: {
    empty: 68,
    laden: 133,
  },
  squadron: {
    empty: 43,
    laden: 195,
  },
}

export const CARRIER_TRADE_COST_TOOLTIP = 'Assumes one 500 LY empty jump and one 500 LY laden jump, tritium at 70,000 Cr/t, and hull maintenance at 100,000 Cr per jump.'

export function carrierTradeCosts(isSquadronCarrier = false) {
  const tonnes = isSquadronCarrier ? CARRIER_TRITIUM_TONNES.squadron : CARRIER_TRITIUM_TONNES.fleet
  const tritiumTonnes = tonnes.empty + tonnes.laden
  const tritiumCost = tritiumTonnes * TRITIUM_PRICE_PER_TONNE
  const hullCost = TRADE_JUMP_COUNT * HULL_MAINTENANCE_PER_JUMP
  return {
    emptyTritiumTonnes: tonnes.empty,
    ladenTritiumTonnes: tonnes.laden,
    tritiumTonnes,
    tritiumCost,
    hullCost,
    totalCost: tritiumCost + hullCost,
  }
}
