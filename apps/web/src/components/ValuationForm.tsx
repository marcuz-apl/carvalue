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
  const [category, setCategory] = useState<string>(initialValues?.category || "pickup");
  const [make, setMake] = useState<string>(initialValues?.make || "Ford");
  const [model, setModel] = useState<string>(initialValues?.model || "F-150");
  const [year, setYear] = useState<number>(initialValues?.year || 2021);
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

  // Compute available makes for current category
  const availableMakes = React.useMemo(() => {
    if (!taxonomy) return ["Ford", "RAM", "Chevrolet", "GMC", "Toyota", "Nissan", "Honda", "Jeep", "Hyundai"];
    if (category === "all" || !taxonomy.models_by_category || !taxonomy.models_by_category[category]) {
      return taxonomy.makes && taxonomy.makes.length > 0 ? taxonomy.makes : Object.keys(taxonomy.models_by_make);
    }
    const catMakes = Object.keys(taxonomy.models_by_category[category] || {});
    return catMakes.length > 0 ? catMakes.sort() : taxonomy.makes;
  }, [taxonomy, category]);

  // Update make if current make is not available in selected category
  useEffect(() => {
    if (availableMakes.length > 0 && !availableMakes.includes(make)) {
      setMake(availableMakes[0]);
    }
  }, [availableMakes, make]);

  // Compute available models for current make and category
  const availableModels = React.useMemo(() => {
    if (!taxonomy) return ["F-150", "Ranger", "1500", "Silverado 1500", "RAV4", "Civic"];
    if (category !== "all" && taxonomy.models_by_category && taxonomy.models_by_category[category] && taxonomy.models_by_category[category][make]) {
      return taxonomy.models_by_category[category][make].sort();
    }
    return (taxonomy.models_by_make[make] || []).sort();
  }, [taxonomy, category, make]);

  // Update model when make or category changes
  useEffect(() => {
    if (availableModels.length > 0 && !availableModels.includes(model)) {
      setModel(availableModels[0]);
    }
  }, [availableModels, model]);

  // Update trims when make/model changes
  const trimKey = `${make}:${model}`;
  const availableTrims = taxonomy?.trims_by_model[trimKey] || ["Base", "LT", "XLT", "Lariat", "Limited", "Sport"];
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
      category,
      drivetrain,
      seller_type: sellerType,
      dataset_filter: datasetFilter,
    });
  };

  const years = Array.from({ length: 25 }, (_, i) => 2024 - i);

  return (
    <form
      onSubmit={handleSubmit}
      className="glass-card"
      id="valuation-form"
      aria-label="Alberta Vehicle Valuation Form"
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

      {/* Vehicle Category Switcher */}
      <div className="form-group" style={{ marginBottom: "1.25rem" }}>
        <label className="form-label" style={{ display: "flex", justifyContent: "space-between" }}>
          <span>Vehicle Category</span>
          <span style={{ fontSize: "0.75rem", color: "var(--accent-primary)", fontWeight: 600 }}>
            {category === "pickup"
              ? "🛻 Pickup Trucks (7,642 listings)"
              : category === "suv"
              ? "🚙 SUVs & Crossovers (21,890 listings)"
              : category === "sedan"
              ? "🚗 Sedans (7,631 listings)"
              : category === "hatchback"
              ? "🚘 Hatchbacks (3,177 listings)"
              : category === "van"
              ? "🚐 Vans & Minivans (2,006 listings)"
              : category === "coupe"
              ? "🏎️ Coupes & Sport (1,243 listings)"
              : "⚡ All Vehicle Types (44,412 listings)"}
          </span>
        </label>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "0.4rem" }}>
          <button
            type="button"
            className={`radio-btn ${category === "pickup" ? "active" : ""}`}
            style={{ fontSize: "0.75rem", padding: "0.45rem 0.2rem", textAlign: "center" }}
            onClick={() => setCategory("pickup")}
          >
            🛻 Pickup
          </button>
          <button
            type="button"
            className={`radio-btn ${category === "suv" ? "active" : ""}`}
            style={{ fontSize: "0.75rem", padding: "0.45rem 0.2rem", textAlign: "center" }}
            onClick={() => setCategory("suv")}
          >
            🚙 SUV
          </button>
          <button
            type="button"
            className={`radio-btn ${category === "sedan" ? "active" : ""}`}
            style={{ fontSize: "0.75rem", padding: "0.45rem 0.2rem", textAlign: "center" }}
            onClick={() => setCategory("sedan")}
          >
            🚗 Sedan
          </button>
          <button
            type="button"
            className={`radio-btn ${category === "hatchback" ? "active" : ""}`}
            style={{ fontSize: "0.75rem", padding: "0.45rem 0.2rem", textAlign: "center" }}
            onClick={() => setCategory("hatchback")}
          >
            🚘 Hatchback
          </button>
          <button
            type="button"
            className={`radio-btn ${category === "van" ? "active" : ""}`}
            style={{ fontSize: "0.75rem", padding: "0.45rem 0.2rem", textAlign: "center" }}
            onClick={() => setCategory("van")}
          >
            🚐 Van / Minivan
          </button>
          <button
            type="button"
            className={`radio-btn ${category === "coupe" ? "active" : ""}`}
            style={{ fontSize: "0.75rem", padding: "0.45rem 0.2rem", textAlign: "center" }}
            onClick={() => setCategory("coupe")}
          >
            🏎️ Coupe
          </button>
        </div>
      </div>

      {/* Make & Model Row */}
      <div className="form-row">
        <div className="form-group">
          <label className="form-label" htmlFor="select-make">
            Vehicle Make
          </label>
          <select
            id="select-make"
            className="form-control"
            value={make}
            onChange={(e) => setMake(e.target.value)}
          >
            {availableMakes.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="select-model">
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
          <label className="form-label" htmlFor="select-year">
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
          <label className="form-label" htmlFor="select-trim">
            Trim / Package
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

      {/* Mileage & Drivetrain Row */}
      <div className="form-row">
        <div className="form-group">
          <label className="form-label" htmlFor="input-mileage">
            Odometer (km)
          </label>
          <input
            type="number"
            id="input-mileage"
            className="form-control"
            value={mileageKm}
            min={0}
            max={800000}
            step={1000}
            onChange={(e) => setMileageKm(Number(e.target.value))}
            placeholder="e.g. 65000"
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label">Drivetrain</label>
          <div className="radio-group" role="radiogroup" aria-label="Drivetrain">
            <button
              type="button"
              id="btn-drivetrain-4wd"
              className={`radio-btn ${drivetrain === "4wd" ? "active" : ""}`}
              onClick={() => setDrivetrain("4wd")}
            >
              4WD / AWD
            </button>
            <button
              type="button"
              id="btn-drivetrain-2wd"
              className={`radio-btn ${drivetrain === "2wd" ? "active" : ""}`}
              onClick={() => setDrivetrain("2wd")}
            >
              2WD (RWD/FWD)
            </button>
          </div>
        </div>
      </div>

      {/* Seller Type Row */}
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Seller Channel</label>
          <div className="radio-group" role="radiogroup" aria-label="Seller Type">
            <button
              type="button"
              id="btn-seller-dealer"
              className={`radio-btn ${sellerType === "dealer" ? "active" : ""}`}
              onClick={() => setSellerType("dealer")}
            >
              Dealership Listing
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

      {/* Dataset Evidence Scope Filter */}
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
              <circle cx="12" cy="10" strokeOpacity="0.25" />
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
