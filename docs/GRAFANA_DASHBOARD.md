# Grafana Dashboard for otel-demo

## Overview

This dashboard visualizes Flask application metrics for otel-demo, including:

- HTTP request rate and total requests
- Error rate (5xx responses)
- Request duration percentiles (p50, p95, p99)
- Pod resource usage (CPU and Memory)
- Request distribution by status code

## Dashboard Panels

### 1. HTTP Request Rate

**Type:** Time Series
**Query:** `rate(flask_http_request_total{job="otel-demo"}[5m])`
**Description:** Shows the rate of HTTP requests per second, broken down by method and status code.

### 2. Total Requests

**Type:** Stat
**Query:** `sum(flask_http_request_total{job="otel-demo"})`
**Description:** Displays the total number of requests processed since application start.

### 3. Error Rate (5xx)

**Type:** Stat
**Query:** `sum(rate(flask_http_request_total{job="otel-demo",status=~"5.."}[5m])) / sum(rate(flask_http_request_total{job="otel-demo"}[5m]))`
**Description:** Shows the percentage of requests returning 5xx errors.

### 4. Request Duration (Percentiles)

**Type:** Time Series
**Queries:**

- p50: `histogram_quantile(0.50, sum(rate(flask_http_request_duration_seconds_bucket{job="otel-demo"}[5m])) by (le, method))`
- p95: `histogram_quantile(0.95, sum(rate(flask_http_request_duration_seconds_bucket{job="otel-demo"}[5m])) by (le, method))`
- p99: `histogram_quantile(0.99, sum(rate(flask_http_request_duration_seconds_bucket{job="otel-demo"}[5m])) by (le, method))`

**Description:** Visualizes request latency at different percentiles to identify slow requests.

### 5. Pod Memory Usage

**Type:** Time Series
**Query:** `container_memory_working_set_bytes{namespace="otel-demo",container="otel-demo"}`
**Description:** Tracks memory consumption of the otel-demo pod.

### 6. Pod CPU Usage

**Type:** Time Series
**Query:** `rate(container_cpu_usage_seconds_total{namespace="otel-demo",container="otel-demo"}[5m])`
**Description:** Shows CPU utilization as a percentage of core time.

### 7. Requests by Status Code

**Type:** Pie Chart
**Query:** `sum by(status) (flask_http_request_total{job="otel-demo"})`
**Description:** Pie chart showing the distribution of HTTP status codes (200, 404, 500, etc.).

## Dashboard Location

The otel-demo dashboard is managed centrally in the **homeassistant** repository:

**Location:** `homeassistant/infrastructure/grafana/dashboards/otel-demo-flask-metrics.json`

This allows unified dashboard management alongside other infrastructure dashboards (PostgreSQL, OAuth2 Proxy, Node Exporter, etc.).

## Installation

### Automated Deployment (Recommended)

The dashboard is automatically deployed via the Grafana restore script:

```bash
# From homeassistant repository
cd infrastructure/grafana
bash scripts/restore-dashboards.sh
```

This script imports all dashboards from `dashboards/` into Grafana at <http://192.168.1.175:3001>.

### Manual Import via Grafana UI

1. Open Grafana at <http://192.168.1.175:3001>
2. Navigate to **Dashboards** → **Import**
3. Click **Upload JSON file**
4. Select `otel-demo-flask-metrics.json` from homeassistant repo
5. Click **Import**

### Manual Import via API

```bash
# From homeassistant repository
GRAFANA_URL="http://192.168.1.175:3001"
GRAFANA_USER="admin"
GRAFANA_PASS="${GRAFANA_PASSWORD:-admin}"

# Create import payload
PAYLOAD=$(jq '{dashboard: ., overwrite: true}' \
  infrastructure/grafana/dashboards/otel-demo-flask-metrics.json)

# Import dashboard
curl -X POST \
  -H "Content-Type: application/json" \
  -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  "${GRAFANA_URL}/api/dashboards/db" \
  -d "${PAYLOAD}"
```

## Updating the Dashboard

To modify the dashboard:

1. Make changes in Grafana UI
2. Export the updated dashboard as JSON
3. Save to `homeassistant/infrastructure/grafana/dashboards/otel-demo-flask-metrics.json`
4. Commit and push to version control

```bash
# Backup updated dashboard from Grafana
cd homeassistant/infrastructure/grafana
bash scripts/backup-dashboards.sh
git add dashboards/otel-demo-flask-metrics.json
git commit -m "Update otel-demo dashboard"
git push
```

## Data Source Configuration

The dashboard uses the Prometheus datasource with UID `df9tmra74d98ga`. If your Prometheus datasource has a different UID:

1. After importing, go to **Dashboard Settings** → **JSON Model**
2. Find and replace all occurrences of `"uid": "df9tmra74d98ga"` with your datasource UID
3. Save the dashboard

## Metrics Reference

All metrics are exposed by the Prometheus Flask exporter at `/metrics/prometheus`:

| Metric Name | Type | Description |
|-------------|------|-------------|
| `flask_http_request_total` | Counter | Total HTTP requests by method, status |
| `flask_http_request_duration_seconds_bucket` | Histogram | Request duration buckets |
| `flask_http_request_duration_seconds_count` | Counter | Request duration count |
| `flask_http_request_duration_seconds_sum` | Counter | Request duration sum |
| `flask_exporter_info` | Gauge | Flask exporter version info |
| `container_memory_working_set_bytes` | Gauge | Pod memory usage (from Kubernetes) |
| `container_cpu_usage_seconds_total` | Counter | Pod CPU usage (from Kubernetes) |

## Troubleshooting

### No Data in Panels

1. Verify Prometheus is scraping otel-demo:

   ```bash
   curl -s 'http://192.168.1.160:30090/api/v1/targets' | jq '.data.activeTargets[] | select(.labels.namespace == "otel-demo")'
   ```

2. Check ServiceMonitor is configured:

   ```bash
   kubectl get servicemonitor -n otel-demo otel-demo
   ```

3. Verify metrics are available:

   ```bash
   curl -s 'http://192.168.1.160:30090/api/v1/query?query=flask_http_request_total{job="otel-demo"}' | jq
   ```

### Wrong Datasource UID

If panels show "Data source not found":

1. Find your Prometheus datasource UID in Grafana (**Connections** → **Data Sources** → **Prometheus**)
2. Edit the dashboard JSON and replace `df9tmra74d98ga` with your UID
3. Re-import the dashboard

## Related Documentation

- [Prometheus Metrics Integration](PROMETHEUS_METRICS.md)
- [OpenTelemetry Configuration](OPENTELEMETRY.md)
- [Operations Guide](operations.md)
