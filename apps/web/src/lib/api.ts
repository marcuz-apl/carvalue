import { TaxonomyResponse, ValuationRequest, ValuationResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

export async function fetchTaxonomy(): Promise<TaxonomyResponse> {
  try {
    const res = await fetch(`${API_BASE}/v1/taxonomy`, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`Failed to fetch taxonomy: ${res.status}`);
    }
    return await res.json();
  } catch (err) {
    console.warn("Using fallback taxonomy due to fetch error:", err);
    // Offline fallback taxonomy for Alberta pickups
    return {
      makes: ["Ford", "Chevrolet", "GMC", "Ram", "Toyota", "Nissan"],
      models_by_make: {
        Ford: ["Ranger", "F-150", "Super Duty F-250", "Maverick"],
        Chevrolet: ["Silverado 1500", "Colorado", "Silverado 2500HD"],
        GMC: ["Sierra 1500", "Canyon", "Sierra 2500HD"],
        Ram: ["1500", "2500", "3500"],
        Toyota: ["Tacoma", "Tundra"],
        Nissan: ["Frontier", "Titan"],
      },
      trims_by_model: {
        "Ford:Ranger": ["XL", "XLT", "Lariat", "Raptor", "Tremor"],
        "Ford:F-150": ["XL", "XLT", "Lariat", "King Ranch", "Platinum", "Tremor", "Raptor"],
        "Chevrolet:Silverado 1500": ["WT", "Custom", "LT", "RST", "LTZ", "High Country", "ZR2"],
        "GMC:Sierra 1500": ["Pro", "SLE", "Elevation", "SLT", "AT4", "Denali", "Denali Ultimate"],
        "Ram:1500": ["Tradesman", "Big Horn", "Laramie", "Rebel", "Limited", "TRX"],
        "Toyota:Tacoma": ["SR", "SR5", "TRD Sport", "TRD Off-Road", "Limited", "TRD Pro"],
      },
    };
  }
}

export async function fetchValuation(
  payload: ValuationRequest,
  valuationDate?: string
): Promise<ValuationResponse> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (valuationDate) {
    headers["x-valuation-date"] = valuationDate;
  }

  const res = await fetch(`${API_BASE}/v1/valuations`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`Valuation error (${res.status}): ${errorBody}`);
  }

  return await res.json();
}
