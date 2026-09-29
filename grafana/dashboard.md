**Dashboard name:** Weather Metrics

---

## Row 1 — current values 

| Panel title | Type | Query (PromQL) | Legend | Unit | Value calculation |  Notes | 
|---|---|---|---|---|---|---|
| Temperature Now | Bar gauge | `weather_temperature_celsius` | `{{location}}` | Celsius (°C) | Last | Min: -40, Max: 50 |
| Humidity Now | Gauge | `weather_humidity_percent`  | `{{location}}` | Percent (0-100) | Last | Min: 0, Max: 100 | 
| Wind Speed Now | Bar gauge | `weather_wind_speed_mps`  | `{{location}}`  | velocity (m/s) | Last | Min: 0, Max: Auto | 

---

## Row 2 — trends over time

| Panel title | Type | Query (PromQL) | Legend | Unit |
|---|---|---|---|---|
| Temperature Over Time (°C) | Time series | `weather_temperature_celsius` | `{{location}}` | Celsius (°C) |
| Humidity Over Time (%) | Time series | `weather_humidity_percent` | `{{location}}` | Percent (0-100) |
| Wind Speed Over Time (m/s) | Time series | `weather_wind_speed_mps` | `{{location}}` | velocity (m/s) |
