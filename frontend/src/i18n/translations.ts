export type Language = 'en' | 'sv'

export interface Translations {
  // Header
  dashboardTitle: string
  dateFrom: string
  dateTo: string
  logout: string
  // Authentication
  loginTitle: string
  loginSubtitle: string
  loginEmail: string
  loginPassword: string
  loginButton: string
  loginSigningIn: string
  loginCheckingSession: string
  loginInvalidCredentials: string
  loginError: string
  loginAdminNotAvailable: string
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
  newConversation: string
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
  // Agent visualizations
  vizNoMetrics: string
  vizNoChartData: string
  vizNoRows: string
  vizNoValidColumns: string
  vizUnsupported: string
  vizRenderError: string
  vizMissingDataset: (dataset: string) => string
}

export const translations: Record<Language, Translations> = {
  en: {
    dashboardTitle: 'Supplier Dashboard',
    dateFrom: 'From',
    dateTo: 'To',
    logout: 'Log out',
    loginTitle: 'Sign in',
    loginSubtitle: 'Use your supplier account to access the dashboard.',
    loginEmail: 'Email',
    loginPassword: 'Password',
    loginButton: 'Sign in',
    loginSigningIn: 'Signing in…',
    loginCheckingSession: 'Checking session…',
    loginInvalidCredentials: 'Incorrect email or password.',
    loginError: 'Could not sign in. Please try again.',
    loginAdminNotAvailable:
      'Retailer admin supplier selection is not available in the current MVP UI.',
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
    newConversation: 'New conversation',
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
    vizNoMetrics: 'No metrics available to display.',
    vizNoChartData: 'No valid data to chart.',
    vizNoRows: 'No rows to display.',
    vizNoValidColumns: 'No valid table columns were provided.',
    vizUnsupported: 'Unsupported visualization type.',
    vizRenderError: 'This visualization could not be rendered.',
    vizMissingDataset: (dataset) => `No visualization dataset "${dataset}".`,
  },
  sv: {
    dashboardTitle: 'Leverantörspanel',
    dateFrom: 'Från',
    dateTo: 'Till',
    logout: 'Logga ut',
    loginTitle: 'Logga in',
    loginSubtitle: 'Använd ditt leverantörskonto för att öppna panelen.',
    loginEmail: 'E-post',
    loginPassword: 'Lösenord',
    loginButton: 'Logga in',
    loginSigningIn: 'Loggar in…',
    loginCheckingSession: 'Kontrollerar session…',
    loginInvalidCredentials: 'Fel e-postadress eller lösenord.',
    loginError: 'Det gick inte att logga in. Försök igen.',
    loginAdminNotAvailable:
      'Val av leverantör för återförsäljaradmin finns inte i MVP-gränssnittet ännu.',
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
    newConversation: 'Ny konversation',
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
    vizNoMetrics: 'Inga mätvärden att visa.',
    vizNoChartData: 'Ingen giltig data att visualisera.',
    vizNoRows: 'Inga rader att visa.',
    vizNoValidColumns: 'Inga giltiga tabellkolumner angavs.',
    vizUnsupported: 'Visualiseringstypen stöds inte.',
    vizRenderError: 'Visualiseringen kunde inte renderas.',
    vizMissingDataset: (dataset) => `Visualiseringsdata "${dataset}" saknas.`,
  },
}


const visualizationFieldLabels: Record<Language, Record<string, string>> = {
  en: {
    rank: 'Rank',
    entity_name: 'Entity',
    entity_type: 'Entity type',
    product_id: 'Product ID',
    product_name: 'Product',
    category: 'Category',
    store_id: 'Store ID',
    store_name: 'Store',
    city: 'City',
    channel: 'Channel',
    period: 'Period',
    period_start: 'Period',
    period_label: 'Period',
    series_name: 'Series',
    units: 'Units sold',
    net_sales: 'Net sales',
    gross_sales: 'Gross sales',
    orders: 'Orders',
    discounts: 'Discounts',
    average_selling_price: 'Average selling price',
    discount_rate: 'Discount rate',
    share_of_rank_metric: 'Share of ranked metric',
    previous_rank_metric_value: 'Previous value',
    rank_metric_absolute_change: 'Absolute change',
    rank_metric_percent_change: 'Percent change',
    total_population_rank_metric_value: 'Population total',
    returned_rows_rank_metric_value: 'Displayed rows total',
  },
  sv: {
    rank: 'Placering',
    entity_name: 'Namn',
    entity_type: 'Typ',
    product_id: 'Produkt-ID',
    product_name: 'Produkt',
    category: 'Kategori',
    store_id: 'Butiks-ID',
    store_name: 'Butik',
    city: 'Stad',
    channel: 'Kanal',
    period: 'Period',
    period_start: 'Period',
    period_label: 'Period',
    series_name: 'Serie',
    units: 'Sålda enheter',
    net_sales: 'Nettoomsättning',
    gross_sales: 'Bruttoomsättning',
    orders: 'Beställningar',
    discounts: 'Rabatter',
    average_selling_price: 'Genomsnittligt försäljningspris',
    discount_rate: 'Rabattgrad',
    share_of_rank_metric: 'Andel av rankningsmått',
    previous_rank_metric_value: 'Föregående värde',
    rank_metric_absolute_change: 'Absolut förändring',
    rank_metric_percent_change: 'Procentuell förändring',
    total_population_rank_metric_value: 'Totalt för populationen',
    returned_rows_rank_metric_value: 'Totalt för visade rader',
  },
}

const visualizationValueLabels: Record<Language, Record<string, string>> = {
  en: {
    online: 'Online',
    physical: 'Physical',
  },
  sv: {
    online: 'Online',
    physical: 'Fysisk',
  },
}

function fallbackHumanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

export function visualizationFieldLabel(
  language: Language,
  key: string,
): string {
  return visualizationFieldLabels[language][key] ?? fallbackHumanizeKey(key)
}

export function visualizationValueLabel(
  language: Language,
  value: unknown,
): unknown {
  if (typeof value !== 'string') return value

  const translated = visualizationValueLabels[language][value.toLowerCase()]
  return translated ?? value
}
