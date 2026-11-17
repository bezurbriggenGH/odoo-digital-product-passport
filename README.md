# Digital Product Passport for Odoo 18

An Odoo 18 module that gives products an EU-style **Digital Product Passport** (in the spirit of the
EU Ecodesign for Sustainable Products Regulation, ESPR), with an automatic **carbon footprint** and a
**public page reachable through a QR code**.

> Guía en español para empezar desde cero: [GUIA.md](GUIA.md)

## Features
- **Material composition** per product: component, material, weight, recycled content, country of origin.
- **Carbon footprint (kg CO2e)**: materials (virgin and recycled emission factors) + manufacturing + transport,
  recomputed automatically whenever a weight, percentage or emission factor changes.
- **Circularity indicators**: recyclable share, recycled content, repairability score, lifetime, spare parts.
- **A–E footprint rating** based on kg CO2e per kg of product (illustrative bands).
- **Public passport page** at `/passport/<token>`: no login, mobile-friendly, light/dark mode.
- **JSON endpoint** at `/passport/<token>/json` for machine-readable access.
- **Printable QR label** (PDF report).
- Random, revocable tokens so passport URLs cannot be guessed.
- Automated tests (`TransactionCase` + `HttpCase`).

## Quick start
Requirements: Docker Desktop.

```bash
docker compose up -d
```

1. Open http://localhost:8069 and create a database named **`dpp`** (master password in `config/odoo.conf`), with demo data.
2. Apps → search "Digital Passport" → Install.
3. Open *Digital Passport → Passports → Electric City Bike*.

## Run the tests
```bash
docker compose run --rm odoo odoo -d dpp_test -i product_digital_passport --test-enable --test-tags /product_digital_passport --stop-after-init --db-filter=^dpp_test$
```

## Project layout
```
addons/product_digital_passport/
├── models/        dpp.material, dpp.product.material, product.template extension
├── controllers/   public passport page and JSON endpoint
├── views/         backend views, menus, public QWeb page
├── report/        QR label (PDF)
├── data/ demo/    starter materials and demo products
└── tests/         unit and HTTP tests
```

## Data disclaimer
Bundled emission factors are illustrative order-of-magnitude values for demonstration only.
Use a recognised source (ecoinvent, DEFRA/DESNZ, ADEME Base Empreinte) for real assessments.

## Roadmap
Spanish translation · per-serial-number passports (`stock.lot`) · footprint from bills of materials (`mrp`) ·
scope 3 emissions from purchases · OWL dashboard · GitHub Actions CI · GS1 Digital Link.

## License
LGPL-3
