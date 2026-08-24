/**
 * TypeScript types matching FastAPI /v1/ contracts.
 */

export interface ValuationRequest {
  make: string;
  model: string;
  year: number;
  mileage_km: number;
  trim?: string;
  drivetrain?: "2wd" | "4wd";
  seller_type?: "dealer" | "private";
}

export type ConfidenceLevel = "high" | "medium" | "low" | "insufficient_data";

export interface ValuationResponse {
  estimate_cad: number;
  interval_low_cad: number;
  interval_high_cad: number;
  confidence_label: ConfidenceLevel;
  comparables_count: number;
  data_freshness_days: number;
  valuation_date: string;
  disclaimer: string;
}

export interface TaxonomyResponse {
  makes: string[];
  models_by_make: Record<string, string[]>;
  trims_by_model: Record<string, string[]>;
}

export interface FeedbackRequest {
  event_id?: number;
  useful: boolean;
  notes?: string;
}
