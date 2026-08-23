# Authorized Ford Ranger contract fixture

`valid.csv` is a small, sanitized fixture derived only from vehicle and listing
facts in the project-owner-provided Ford Ranger workbook. The project owner
authorizes it for local development and automated testing in this repository.

It contains only model year, odometer kilometres, asking price in CAD, vehicle
configuration, Alberta province, a synthetic fixture record ID, and observation
date. It contains no seller identity, contact information, personal free text,
photos, VINs, canonical URLs, or raw source content.

The generic `Price` header is accepted only when the import caller supplies
explicit `ImportContext(currency_code="CAD")` evidence. The fixture header alone
does not establish or infer currency.

This fixture is not production market data, must not be used to train or
evaluate a production valuation model, and must never be used to enable a live
source adapter, network collection, or any automated source.
