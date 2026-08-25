"use client";

import React, { useEffect, useState } from "react";
import { fetchTaxonomy } from "../lib/api";
import { TaxonomyResponse, ValuationRequest } from "../lib/types";

interface ValuationFormProps {
  onSubmit: (request: ValuationRequest) => void;
  isLoading: boolean;
  initialValues?: Partial<ValuationRequest>;
}

export default function ValuationForm({
  onSubmit,
  isLoading,
  initialValues,
}: ValuationFormProps) {
  const [taxonomy, setTaxonomy] = useState<TaxonomyResponse | null>(null);
  const [make, setMake] = useState<string>(initialValues?.make || "Ford");
  const [model, setModel] = useState<string>(initialValues?.model || "Ranger");
  const [year, setYear] = useState<number>(initialValues?.year || 2022);
  const [mileageKm, setMileageKm] = useState<number>(initialValues?.mileage_km || 45000);
  const [trim, setTrim] = useState<string>(initialValues?.trim || "XLT");
  const [drivetrain, setDrivetrain] = useState<"2wd" | "4wd">(
    initialValues?.drivetrain || "4wd"
  );
  const [sellerType, setSellerType] = useState<"dealer" | "private">(
    initialValues?.seller_type || "dealer"
  );
  const [datasetFilter, setDatasetFilter] = useState<"real_only" | "all" | "synthetic_only">(
    initialValues?.dataset_filter || "real_only"
  );

  useEffect(() => {
    fetchTaxonomy().then(setTaxonomy).catch(console.error);
  }, []);

  // Update models when make changes
  const availableModels = taxonomy?.models_by_make[make] || ["Ranger", "F-150"];
  useEffect(() => {
    if (availableModels.length > 0 && !availableModels.includes(model)) {
      setModel(availableModels[0]);
    }
  }, [make, availableModels, model]);

  // Update trims when make/model changes
  const trimKey = `${make}:${model}`;
  const availableTrims = taxonomy?.trims_by_model[trimKey] || ["XL", "XLT", "Lariat"];
  useEffect(() => {
    if (availableTrims.length > 0 && !availableTrims.includes(trim)) {
      setTrim(availableTrims[0]);
    }
  }, [trimKey, availableTrims, trim]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      make,
      model,
      year,
      mileage_km: Number(mileageKm),
      trim,
      drivetrain,
      seller_type: sellerType,
      dataset_filter: datasetFilter,
    });
  };


  const years = Array.from({ length: 16 }, (_, i) => 2025 - i);

  return (
    <form
      onSubmit={handleSubmit}
      className="glass-card"
      id="valuation-form"
      aria-label="Alberta Pickup Valuation Form"
    >
      <h2 className="form-title" id="form-title">
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{ color: "var(--accent-primary)" }}
        >
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
        Vehicle Specifications
      </h2>

      {/* Make & Model Row */}
      <div className="form-row">
        <div className="form-group">
          <label htmlFor="select-make" className="form-label">
            Make
          </label>
          <select
            id="select-make"
            className="form-control"
            value={make}
            onChange={(e) => setMake(e.target.value)}
          >
            {(taxonomy?.makes || ["Ford", "Chevrolet", "GMC", "Ram", "Toyota", "Nissan"]).map(
              (m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              )
            )}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="select-model" className="form-label">
            Model
          </label>
          <select
            id="select-model"
            className="form-control"
            value={model}
            onChange={(e) => setModel(e.target.value)}
          >
            {availableModels.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Year & Trim Row */}
      <div className="form-row">
        <div className="form-group">
          <label htmlFor="select-year" className="form-label">
            Model Year
          </label>
          <select
            id="select-year"
            className="form-control"
            value={year}
            onChange={(e) => setYear(Number(e.target.value))}
          >
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label htmlFor="select-trim" className="form-label">
            Trim Package
          </label>
          <select
            id="select-trim"
            className="form-control"
            value={trim}
            onChange={(e) => setTrim(e.target.value)}
          >
            {availableTrims.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Mileage in km */}
      <div className="form-group">
        <label htmlFor="input-mileage" className="form-label">
          Odometer (Kilometres)
        </label>
        <input
          type="number"
          id="input-mileage"
          className="form-control"
          min={0}
          max={800000}
          step={500}
          value={mileageKm}
          onChange={(e) => setMileageKm(Math.max(0, Number(e.target.value)))}
          placeholder="e.g. 45000"
          required
        />
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginTop: "0.35rem",
            fontSize: "0.75rem",
            color: "var(--text-muted)",
          }}
        >
          <span>Current: {Number(mileageKm).toLocaleString()} km</span>
          <span>Alberta pickup standard</span>
        </div>
      </div>

      {/* Drivetrain & Seller Type Row */}
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Drivetrain</label>
          <div className="radio-group">
            <button
              type="button"
              id="btn-drivetrain-4wd"
              className={`radio-btn ${drivetrain === "4wd" ? "active" : ""}`}
              onClick={() => setDrivetrain("4wd")}
            >
              4WD / 4x4
            </button>
            <button
              type="button"
              id="btn-drivetrain-2wd"
              className={`radio-btn ${drivetrain === "2wd" ? "active" : ""}`}
              onClick={() => setDrivetrain("2wd")}
            >
              2WD / RWD
            </button>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Seller Type</label>
          <div className="radio-group">
            <button
              type="button"
              id="btn-seller-dealer"
              className={`radio-btn ${sellerType === "dealer" ? "active" : ""}`}
              onClick={() => setSellerType("dealer")}
            >
              Dealer Listing
            </button>
            <button
              type="button"
              id="btn-seller-private"
              className={`radio-btn ${sellerType === "private" ? "active" : ""}`}
              onClick={() => setSellerType("private")}
            >
              Private Seller
            </button>
          </div>
        </div>
      </div>

      {/* Dataset Provenance Filter */}
      <div className="form-group" style={{ marginTop: "0.25rem", marginBottom: "1rem" }}>
        <label className="form-label" style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Data Evidence Scope</span>
          <span style={{ fontSize: "0.75rem", color: "var(--accent-primary)", fontWeight: 500 }}>
            {datasetFilter === "real_only"
              ? "🟢 Real 2022 Canadian Dealer Dataset"
              : datasetFilter === "all"
              ? "📊 Combined (Real + Simulator Demo)"
              : "🧪 Simulated Benchmark Only"}
          </span>
        </label>
        <div className="radio-group" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "0.5rem" }}>
          <button
            type="button"
            id="btn-dataset-real"
            className={`radio-btn ${datasetFilter === "real_only" ? "active" : ""}`}
            style={{ fontSize: "0.8rem", padding: "0.45rem 0.25rem", textAlign: "center" }}
            onClick={() => setDatasetFilter("real_only")}
          >
            🟢 Real Dealer (2022)
          </button>
          <button
            type="button"
            id="btn-dataset-all"
            className={`radio-btn ${datasetFilter === "all" ? "active" : ""}`}
            style={{ fontSize: "0.8rem", padding: "0.45rem 0.25rem", textAlign: "center" }}
            onClick={() => setDatasetFilter("all")}
          >
            📊 All Sources
          </button>
          <button
            type="button"
            id="btn-dataset-synthetic"
            className={`radio-btn ${datasetFilter === "synthetic_only" ? "active" : ""}`}
            style={{ fontSize: "0.8rem", padding: "0.45rem 0.25rem", textAlign: "center" }}
            onClick={() => setDatasetFilter("synthetic_only")}
          >
            🧪 Simulated Only
          </button>
        </div>
      </div>


      <button
        type="submit"
        id="btn-submit-valuation"
        className="submit-btn"
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <svg
              className="animate-spin"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" strokeOpacity="0.25" />
              <path d="M12 2a10 10 0 0 1 10 10" />
            </svg>
            Calculating Alberta Market Estimate...
          </>
        ) : (
          <>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
            Get Asking-Price Estimate
          </>
        )}
      </button>
    </form>
  );
}
