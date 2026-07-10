import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts'
import { COLORS, formatShortNumber, formatTooltipValue } from './visualizationUtils'
import { useTranslation } from '../../../i18n/LanguageContext'

interface StoreBreakdownChartProps {
  rows: Array<Record<string, unknown>>
  loading: boolean
}

export function StoreBreakdownChart({ rows, loading }: StoreBreakdownChartProps) {
  const { t } = useTranslation()

  if (loading) return <div className="chart-placeholder">{t.loading}</div>
  if (!rows.length) return <div className="chart-placeholder">{t.noStoreData}</div>

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={rows} margin={{ top: 4, right: 16, left: 0, bottom: 32 }}>
        <XAxis
          dataKey="group_name"
          tick={{ fontSize: 11 }}
          angle={-30}
          textAnchor="end"
          interval={0}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          tickFormatter={(v: number) => formatShortNumber(v)}
          width={44}
        />
        <Tooltip formatter={(v) => formatTooltipValue(v)} />
        <Bar
          dataKey="value"
          name={t.netSales}
          fill={COLORS[0]}
          radius={[3, 3, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
