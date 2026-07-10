export type Language = 'en' | 'sv'

export interface Translations {
  // Header
  dashboardTitle: string
  dateFrom: string
  dateTo: string
  // KPI cards
  netSales: string
  grossSales: string
  unitsSold: string
  orders: string
  // Column / metric labels
  units: string
  discounts: string
  // Section headings
  productRevenueTrend: string
  topProducts: string
  storeBreakdown: string
  chat: string
  // Chat panel
  chatPlaceholder: string
  chatEmpty: string
  chatThinking: string
  chatSend: string
  chatError: string
  // Shared states
  loading: string
  // TopProductsTable
  noProducts: string
  colProduct: string
  colCategory: string
  sortBy: (label: string) => string
  // ProductTimeseriesChart
  grain: string
  grainMonth: string
  grainWeek: string
  metric: string
  productsSelected: (n: number) => string
  productsTop5: string
  clearSelection: string
  noTimeseriesData: string
  // StoreBreakdownChart
  noStoreData: string
}

export const translations: Record<Language, Translations> = {
  en: {
    dashboardTitle: 'Supplier Dashboard',
    dateFrom: 'From',
    dateTo: 'To',
    netSales: 'Net Sales',
    grossSales: 'Gross Sales',
    unitsSold: 'Units Sold',
    orders: 'Orders',
    units: 'Units',
    discounts: 'Discounts',
    productRevenueTrend: 'Product Revenue Trend',
    topProducts: 'Top Products',
    storeBreakdown: 'Store Breakdown',
    chat: 'Chat',
    chatPlaceholder: 'Ask a question…',
    chatEmpty: 'Ask an analytics question, e.g. "Show me my top products"',
    chatThinking: 'Thinking…',
    chatSend: 'Send',
    chatError: 'Request failed. Please try again.',
    loading: 'Loading…',
    noProducts: 'No products found.',
    colProduct: 'Product',
    colCategory: 'Category',
    sortBy: (label) => `Sort by ${label}`,
    grain: 'Grain',
    grainMonth: 'Month',
    grainWeek: 'Week',
    metric: 'Metric',
    productsSelected: (n) => `Products (${n} selected)`,
    productsTop5: 'Products (top 5)',
    clearSelection: 'Clear',
    noTimeseriesData: 'No timeseries data available.',
    noStoreData: 'No store breakdown data available.',
  },
  sv: {
    dashboardTitle: 'Leverantörspanel',
    dateFrom: 'Från',
    dateTo: 'Till',
    netSales: 'Nettoomsättning',
    grossSales: 'Bruttoomsättning',
    unitsSold: 'Sålda enheter',
    orders: 'Beställningar',
    units: 'Enheter',
    discounts: 'Rabatter',
    productRevenueTrend: 'Produktomsättningstrend',
    topProducts: 'Topprodukter',
    storeBreakdown: 'Butiksfördelning',
    chat: 'Chatt',
    chatPlaceholder: 'Ställ en fråga…',
    chatEmpty: 'Ställ en analysfråga, t.ex. "Visa mina topprodukter"',
    chatThinking: 'Tänker…',
    chatSend: 'Skicka',
    chatError: 'Förfrågan misslyckades. Försök igen.',
    loading: 'Laddar…',
    noProducts: 'Inga produkter hittades.',
    colProduct: 'Produkt',
    colCategory: 'Kategori',
    sortBy: (label) => `Sortera efter ${label}`,
    grain: 'Granularitet',
    grainMonth: 'Månad',
    grainWeek: 'Vecka',
    metric: 'Mätvärde',
    productsSelected: (n) => `Produkter (${n} valda)`,
    productsTop5: 'Produkter (topp 5)',
    clearSelection: 'Rensa',
    noTimeseriesData: 'Ingen tidsseriedata tillgänglig.',
    noStoreData: 'Ingen butiksdata tillgänglig.',
  },
}
