# ⚡ CCGT-Twin — Digital Twin for Thermal Power Plant Operations

[![Streamlit App](assets/badges/streamlit_badge.svg)](https://ccgt-twin.streamlit.app/)
![Python](assets/badges/python.svg)
![Streamlit](assets/badges/streamlit.svg)
![XGBoost](assets/badges/xgboost.svg)
![License](assets/badges/license.svg)

> Built by a **Shift Supervisor with 15 years of hands-on CCGT experience** — not a data scientist who read about power plants.  
> Every parameter, every constraint, every decision logic in this app comes from real operational knowledge.

---

## 🌐 Live Demo

👉 **[ccgt-twin.streamlit.app](https://ccgt-twin.streamlit.app/)**

Available in 🇫🇷 French · 🇬🇧 English · 🇪🇸 Spanish · 🇮🇹 Italian

---

## 🎯 The Problem This Solves

Operating a CCGT plant means making **real-time decisions under pressure** :

- Is it worth activating the fogging system right now, given current air conditions ?
- What is our maximum deliverable power for tomorrow's market bid ?
- The grid is imbalanced — do we ramp up, and is it financially viable before the signal expires ?

These questions are answered today with experience and intuition. This project answers them with **data**.

The models were trained on **real operational data** extracted from a 400 MW CCGT plant via **PI Web API (OSIsoft PI System)**, stored as **Parquet files compressed with ZStandard**. The digital twin replicates the plant's thermodynamic behaviour with sufficient fidelity for operational decision support.

> ⚠️ **Confidentiality** : Site coordinates, raw data, and model outputs have been anonymised. A multiplicative factor has been applied to power predictions to prevent disclosure of sensitive operational information.

---

## 🧠 Architecture

```
┌──────────────────────────────────────────────────────────┐
│                     Data Pipeline                        │
│  PI System → PI Web API → Python → Parquet (ZStd)        │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│                  ML Models (XGBoost)                     │
│  ┌─────────────────────┐  ┌──────────────────────────┐   │
│  │  jumeau_pmax_v2     │  │   jumeau_rendement       │   │
│  │  Max Power (MW)     │  │   Thermal Efficiency (%) │   │
│  └─────────────────────┘  └──────────────────────────┘   │
└─────────────────────┬────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────┐
│               Streamlit Application                      │
│                                                          │
│  src/                                                    │
│  ├── config.py    # Page settings & shared utilities     │
│  ├── i18n.py      # Translations & language management   │
│  ├── api.py       # Weather API calls & session state    │
│  └── models.py    # ML inference (getPuissance,          │
│                   #              getRendement)           │
│                                                          │
│  pages/                                                  │
│  ├── Fogging.py      # Fogging impact analysis           │
│  ├── Previsions.py   # J+1 / J+2 power forecasting       │
│  ├── Monitoring.py   # Live financial decision dashboard │
│  └── SandBox.py     # Interactive simulator              │
└──────────────────────────────────────────────────────────┘
```

---

## 📦 Modules

### 🔍 Fogging — *"Is it worth starting the pumps?"*
The fogging system cools inlet air to increase air density and boost power output — but only under the right conditions. This module pulls **live weather data** and simulates each pump configuration (0 to 6 pumps) against the digital twin, giving an instant answer with the expected MW gain.

### 📈 Forecasting — *"What can we promise for tomorrow?"*
Generates a **96-slot (15-min) power forecast** for J+1 or J+2 combining :
- [Open-Meteo](https://open-meteo.com/) weather & marine forecast APIs
- Optimal fogging configuration per time slot
- Confidence bands based on model error (MAE)

This is the kind of tool that feeds a **market bid** or a **nomination** to the TSO.

### 💰 Monitoring — *"Should we respond to this imbalance signal?"*
Real-time financial arbitrage dashboard crossing :
- Grid imbalance signal from **[Elia Open Data](https://opendata.elia.be/)** (Belgian TSO)
- Plant marginal cost calculated from the efficiency digital twin (heat rate, gas price, CO₂)
- Ramp timing analysis : can we physically reach the target before the signal expires ?

The output is a clear **ACTION / WAIT / REFUSE** recommendation with estimated financial gain.

### 🧪 SandBox — *"What happens if conditions change?"*
Interactive simulator for training and scenario analysis. Adjust temperature, humidity, pressure, water temperature and fogging configuration — the digital twin recalculates instantly. Sliders initialise automatically with live weather data.

---

## 👤 About

This project was built entirely outside working hours by a **Shift Supervisor** with :

- **15 years of operational experience** on a 400 MW Combined Cycle Gas Turbine
- Full authority over production, safety and personnel (up to 200 people during outages)
- Zero serious accidents over 15 years
- Daily hands-on experience with **DCS ABB 800xA**, **AVEVA PI Vision**, thermodynamic parameters, grid balancing, and emergency procedures

The digital components were self-taught and self-implemented :
- Data extraction via **PI Web API**
- Predictive modelling with **XGBoost**
- Dashboard development with **Streamlit**
- Electronics prototyping with **Raspberry Pi / ESP32**

The combination of deep operational expertise and autonomous technical development is the core value proposition of this project — and of its author.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Data extraction** | Python · PI Web API (OSIsoft PI System) |
| **Data storage** | Apache Parquet · ZStandard compression |
| **ML Models** | XGBoost · scikit-learn · joblib |
| **Weather data** | Open-Meteo API · Marine API |
| **Grid data** | Elia Open Data API |
| **Frontend** | Streamlit · Altair · Pandas · NumPy |
| **Async HTTP** | httpx · asyncio |
| **i18n** | Custom JSON-based translation system (FR/EN/ES/IT) |
| **Deployment** | Streamlit Community Cloud |

---

## 🗂️ Project Structure

```
ccgt-twin/
├── Home.py                      # Landing page & module navigation
├── pages/
│   ├── Fogging.py
│   ├── Previsions.py
│   ├── Monitoring.py
│   └── SandBox.py
├── src/
│   ├── config.py                # Global settings, secrets & shared utilities
│   ├── i18n.py                  # Language management
│   ├── api.py                   # Weather API + session state
│   └── models.py                # ML inference functions
├── config/
│   ├── jumeau_pmax_v2.joblib    # Power digital twin (XGBoost)
│   └── jumeau_rendement.joblib  # Efficiency digital twin (XGBoost)
├── locales/
│   ├── fr.json                  # French
│   ├── en.json                  # English
│   ├── es.json                  # Spanish
│   └── it.json                  # Italian
├── assets/
│   └── logo2.svg
└── requirements.txt
```

---

## ⚙️ Key Technical Decisions

**Separation of fetch and display** — API fetch functions are decorated with `@st.cache_data` and contain no Streamlit UI calls. Public wrapper functions handle error display separately, preventing silent crashes.

**Vectorised batch inference** — The Forecasting module builds a single 672-row DataFrame (96 time slots × 7 pump configs) and calls the XGBoost model once. Typical speedup : 10–50× vs. a naive loop.

**Non-blocking refresh loop** — The Monitoring dashboard uses `st.session_state` + `st.rerun()` instead of a blocking `while True / time.sleep()` loop, keeping the Streamlit thread free for multi-user deployments.

**UTC timestamp storage** — Synchronisation timestamps are stored as Unix UTC and converted to the user's local timezone client-side via JavaScript — correctly handles summer/winter time automatically.

**Unified weather loading** — `update_meteo()` is called at the top of every page. Thanks to `@st.cache_data(ttl=600)`, the actual API call happens at most once every 10 minutes regardless of navigation.

---

## 🚀 Run Locally

```bash
# Clone the repository
git clone https://github.com/Lobo-Energy/ccgt-twin.git
cd ccgt-twin

# Install dependencies
pip install -r requirements.txt

# Launch
streamlit run Home.py
```

### `.streamlit/secrets.toml` (optional)

```toml
[site_config]
LAT_AIR   = YOUR_LAT
LON_AIR   = YOUR_LON
LAT_WATER = YOUR_LAT
LON_WATER = YOUR_LON
NEAR_SEA  = true
```

> If this file is absent, the app automatically falls back to the default coordinates defined in `src/config.py`.

---

## 📄 License

Private repository — all rights reserved.  
Models and data are anonymised. Do not redistribute.

---

*This project exists because operational expertise and digital skills are more powerful together than apart.*
