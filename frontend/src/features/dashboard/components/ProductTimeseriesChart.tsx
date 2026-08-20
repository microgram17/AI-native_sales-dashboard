import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from 'recharts'
import {
  COLORS,
  formatShortNumber,
  formatTooltipValue,
  longToWide,
} from './visualizationUtils'
import type {
  Grain,
  Metric,
  ProductSelectorItem,
  TimeseriesRow,
} from '../../../types/dashboard'
import { useTranslation } from '../../../i18n/LanguageContext'


function stableColorIndex(value: string): number {
  let hash = 0

  for (let index = 0; index < value.length; index += 1) {
    hash = (
      (hash * 31) +
      value.charCodeAt(index)
    ) >>> 0
  }

  return hash % COLORS.length
}

interface ProductTimeseriesChartProps {
  rows: TimeseriesRow[]
  loading: boolean
  grain: Grain
  metric: Metric
  selectedProductIds: string[]
  products: ProductSelectorItem[]
  onGrainChange: (grain: Grain) => void
  onMetricChange: (metric: Metric) => void
  onProductsChange: (ids: string[]) => void
}

export function ProductTimeseriesChart({
  rows,
  loading,
  grain,
  metric,
  selectedProductIds,
  products,
  onGrainChange,
  onMetricChange,
  onProductsChange,
}: ProductTimeseriesChartProps) {
  const { t } = useTranslation()

  const metricLabels: Record<Metric, string> = {
    net_sales: t.netSales,
    gross_sales: t.grossSales,
    units: t.units,
    orders: t.orders,
    discounts: t.discounts,
  }

  function toggleProduct(id: string) {
    if (selectedProductIds.includes(id)) {
      onProductsChange(
        selectedProductIds.filter(
          (productId) => productId !== id,
        ),
      )
      return
    }

    onProductsChange([
      ...selectedProductIds,
      id,
    ])
  }

  return (
    <div className="product-timeseries">
      <div className="product-timeseries-controls">
        <div className="dashboard-control">
          <span className="dashboard-control-label">
            {t.grain}
          </span>

          <div className="grain-toggle">
            {(['month', 'week'] as Grain[]).map(
              (item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() =>
                    onGrainChange(item)
                  }
                  className={
                    grain === item ? 'active' : ''
                  }
                >
                  {item === 'month'
                    ? t.grainMonth
                    : t.grainWeek}
                </button>
              ),
            )}
          </div>
        </div>

        <div className="dashboard-control">
          <label
            className="dashboard-control-label"
            htmlFor="product-trend-metric"
          >
            {t.metric}
          </label>

          <select
            id="product-trend-metric"
            value={metric}
            onChange={(event) =>
              onMetricChange(
                event.target.value as Metric,
              )
            }
            className="dashboard-select"
          >
            {(
              Object.entries(metricLabels) as [
                Metric,
                string,
              ][]
            ).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {products.length > 0 && (
          <div className="dashboard-control product-selector-control">
            <div className="product-selector-heading">
              <span className="dashboard-control-label">
                {selectedProductIds.length > 0
                  ? t.productsSelected(
                      selectedProductIds.length,
                    )
                  : t.productsNoneSelected}
              </span>

              {selectedProductIds.length > 0 && (
                <button
                  type="button"
                  onClick={() =>
                    onProductsChange([])
                  }
                  className="clear-selection-button"
                >
                  {t.clearSelection}
                </button>
              )}
            </div>

            <div className="product-selector-list">
              {products.map((product) => (
                <label
                  key={product.product_id}
                  className="product-selector-item"
                >
                  <input
                    type="checkbox"
                    checked={selectedProductIds.includes(
                      product.product_id,
                    )}
                    onChange={() =>
                      toggleProduct(
                        product.product_id,
                      )
                    }
                  />

                  <span className="product-selector-name">
                    {product.product_name}
                  </span>

                  <span className="product-selector-category">
                    {product.category}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      {loading ? (
        <div className="chart-placeholder">
          {t.loading}
        </div>
      ) : !rows.length ? (
        <div className="chart-placeholder">
          {t.noTimeseriesData}
        </div>
      ) : (
        (() => {
          const {
            wideData,
            seriesValues,
          } = longToWide(
            rows as unknown as Record<
              string,
              unknown
            >[],
            'period',
            'product_name',
            'value',
          )

          if (!wideData.length) {
            return (
              <div className="chart-placeholder">
                {t.noTimeseriesData}
              </div>
            )
          }

          return (
            <ResponsiveContainer
              width="100%"
              height={250}
            >
              <LineChart
                data={wideData}
                margin={{
                  top: 8,
                  right: 18,
                  left: 0,
                  bottom: 4,
                }}
              >
                <XAxis
                  dataKey="period"
                  tick={{
                    fontSize: 11,
                    fill: 'var(--viz-axis)',
                  }}
                  axisLine={{
                    stroke:
                      'var(--viz-axis-line)',
                  }}
                  tickLine={{
                    stroke:
                      'var(--viz-axis-line)',
                  }}
                  interval="preserveStartEnd"
                />

                <YAxis
                  tick={{
                    fontSize: 11,
                    fill: 'var(--viz-axis)',
                  }}
                  axisLine={{
                    stroke:
                      'var(--viz-axis-line)',
                  }}
                  tickLine={{
                    stroke:
                      'var(--viz-axis-line)',
                  }}
                  tickFormatter={(
                    value: number,
                  ) =>
                    formatShortNumber(value)
                  }
                  width={46}
                />

                <Tooltip
                  formatter={(value) =>
                    formatTooltipValue(value)
                  }
                  contentStyle={{
                    background:
                      'var(--viz-tooltip-bg)',
                    border:
                      '1px solid var(--viz-tooltip-border)',
                    borderRadius: '8px',
                    color: 'var(--text-h)',
                  }}
                />

                {seriesValues.length > 1 && (
                  <Legend
                    wrapperStyle={{
                      fontSize: 11,
                    }}
                  />
                )}

                {seriesValues.map(
                  (series) => (
                    <Line
                      key={series}
                      type="monotone"
                      dataKey={series}
                      name={series}
                      stroke={
                        COLORS[
                          stableColorIndex(
                            products.find(
                              (product) =>
                                product.product_name ===
                                series,
                            )?.product_id ??
                              series,
                          )
                        ]
                      }
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  ),
                )}
              </LineChart>
            </ResponsiveContainer>
          )
        })()
      )}
    </div>
  )
}
