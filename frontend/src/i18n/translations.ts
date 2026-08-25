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
  averageOrderValue: string
  unitsPerOrder: string
  // Column / metric labels
  units: string
  discounts: string
  // Section headings
  productRevenueTrend: string
  productTrendTitle: (metricLabel: string) => string
  topProducts: string
  productsTable: string
  storeBreakdown: string
  salesTrendTitle: (metricLabel: string) => string
  performanceTitle: (metricLabel: string, groupLabel: string) => string
  productAnalysis: string
  productAnalysisDescription: string
  groupBy: string
  groupStore: string
  groupCity: string
  groupChannel: string
  onlineStore: string
  channelOnline: string
  channelPhysical: string
  unknownGroup: string
  chat: string
  askSalesData: string
  // Chat panel
  chatPlaceholder: string
  chatEmpty: string
  chatThinking: string
  chatSend: string
  chatError: string
  newConversation: string
  chatSuggestions: string[]
  chatContext: (dateFrom: string, dateTo: string) => string
  explainWithAi: string
  explainKpi: (metricLabel: string) => string
  explainTrend: (metricLabel: string) => string
  explainPerformance: (metricLabel: string, groupLabel: string) => string
  // Shared states
  loading: string
  // TopProductsTable
  noProducts: string
  colProduct: string
  colCategory: string
  sortBy: (label: string) => string
  loadingMoreProducts: string
  productsLoaded: (loaded: number, total: number) => string
  // ProductTimeseriesChart
  grain: string
  grainMonth: string
  grainWeek: string
  metric: string
  productsSelected: (n: number) => string
  productsTop5: string
  clearSelection: string
  productsNoneSelected: string
  noTimeseriesData: string
  // StoreBreakdownChart
  noStoreData: string
  noPerformanceTrendData: string
  view: string
  ranking: string
  trend: string
  addComparison: string
  removeComparison: string
  currentPeriod: string
  previousPeriod: string
  // Agent visualizations
  vizNoMetrics: string
  vizNoChartData: string
  vizNoRows: string
  vizNoValidColumns: string
  vizUnsupported: string
  vizRenderError: string
  rankedBy: string
  rankingMetric: string
  // Export
  export: string
  exporting: string
  exportExcel: string
  exportCsv: string
  exportPng: string
  exportFailed: string
  exportDataSheet: string
  exportFiltersSheet: string
  exportFilter: string
  exportValue: string
  salesSummary: string
  vsPreviousPeriod: string
  exportTopProducts: string
  exportSortedBy: string
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
    averageOrderValue: 'Average Order Value',
    unitsPerOrder: 'Units per Order',
    units: 'Units',
    discounts: 'Discounts',
    productRevenueTrend: 'Product Revenue Trend',
    productTrendTitle: (metricLabel) => `${metricLabel} by product`,
    topProducts: 'Top Products',
    productsTable: 'Products',
    storeBreakdown: 'Store Breakdown',
    salesTrendTitle: (metricLabel) => `${metricLabel} over time`,
    performanceTitle: (metricLabel, groupLabel) =>
      `${metricLabel} by ${groupLabel.toLowerCase()}`,
    productAnalysis: 'Product analysis',
    productAnalysisDescription:
      'Compare individual product performance when you need a deeper view.',
    groupBy: 'Group by',
    groupStore: 'Store',
    groupCity: 'City',
    groupChannel: 'Channel',
    onlineStore: 'Online Store',
    channelOnline: 'Online',
    channelPhysical: 'Physical stores',
    unknownGroup: 'Unknown',
    chat: 'Chat',
    askSalesData: 'Ask your sales data',
    chatPlaceholder: 'Ask a question…',
    chatEmpty: 'Ask an analytics question, e.g. "Show me my top products"',
    chatThinking: 'Thinking…',
    chatSend: 'Send',
    chatError: 'Request failed. Please try again.',
    newConversation: 'New conversation',
    chatSuggestions: [
      'Why did sales change during this period?',
      'Which stores are underperforming?',
      'Compare online and physical sales.',
      'Which products drove the result?',
    ],
    chatContext: (dateFrom, dateTo) => `${dateFrom} – ${dateTo}`,
    explainWithAi: 'Explain with AI',
    explainKpi: (metricLabel) =>
      `Explain the change in ${metricLabel} for the current dashboard period.`,
    explainTrend: (metricLabel) =>
      `Analyze the ${metricLabel} trend in the current dashboard view. What stands out?`,
    explainPerformance: (metricLabel, groupLabel) =>
      `Analyze ${metricLabel} by ${groupLabel.toLowerCase()} in the current dashboard view. What stands out?`,
    loading: 'Loading…',
    noProducts: 'No products found.',
    colProduct: 'Product',
    colCategory: 'Category',
    sortBy: (label) => `Sort by ${label}`,
    loadingMoreProducts: 'Loading more products…',
    productsLoaded: (loaded, total) => `${loaded} of ${total} products`,
    grain: 'Grain',
    grainMonth: 'Month',
    grainWeek: 'Week',
    metric: 'Metric',
    productsSelected: (n) => `Products (${n} selected)`,
    productsTop5: 'Products (top 5)',
    clearSelection: 'Clear',
    productsNoneSelected: 'Products (none selected)',
    noTimeseriesData: 'No timeseries data available.',
    noStoreData: 'No store breakdown data available.',
    noPerformanceTrendData: 'No performance trend data available.',
    view: 'View',
    ranking: 'Ranking',
    trend: 'Trend',
    addComparison: 'Add comparison',
    removeComparison: 'Remove comparison',
    currentPeriod: 'Current period',
    previousPeriod: 'Previous period',
    vizNoMetrics: 'No metrics available to display.',
    vizNoChartData: 'No valid data to chart.',
    vizNoRows: 'No rows to display.',
    vizNoValidColumns: 'No valid table columns were provided.',
    vizUnsupported: 'Unsupported visualization type.',
    vizRenderError: 'This visualization could not be rendered.',
    rankedBy: 'Ranked by',
    rankingMetric: 'Ranking metric',
    export: 'Export',
    exporting: 'Exporting…',
    exportExcel: 'Excel (.xlsx)',
    exportCsv: 'CSV (.csv)',
    exportPng: 'PNG image',
    exportFailed: 'Export failed.',
    exportDataSheet: 'Data',
    exportFiltersSheet: 'Filters',
    exportFilter: 'Filter',
    exportValue: 'Value',
    salesSummary: 'Sales Summary',
    vsPreviousPeriod: 'vs previous period',
    exportTopProducts: 'Top 5 products',
    exportSortedBy: 'Sorted by',
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
    averageOrderValue: 'Genomsnittligt ordervärde',
    unitsPerOrder: 'Enheter per order',
    units: 'Enheter',
    discounts: 'Rabatter',
    productRevenueTrend: 'Produktomsättningstrend',
    productTrendTitle: (metricLabel) => `${metricLabel} per produkt`,
    topProducts: 'Topprodukter',
    productsTable: 'Produkter',
    storeBreakdown: 'Butiksfördelning',
    salesTrendTitle: (metricLabel) => `${metricLabel} över tid`,
    performanceTitle: (metricLabel, groupLabel) =>
      `${metricLabel} per ${groupLabel.toLowerCase()}`,
    productAnalysis: 'Produktanalys',
    productAnalysisDescription:
      'Jämför enskilda produkters utveckling när du behöver mer detaljer.',
    groupBy: 'Gruppera efter',
    groupStore: 'Butik',
    groupCity: 'Stad',
    groupChannel: 'Kanal',
    onlineStore: 'Onlinebutik',
    channelOnline: 'Online',
    channelPhysical: 'Fysiska butiker',
    unknownGroup: 'Okänd',
    chat: 'Chatt',
    askSalesData: 'Fråga din försäljningsdata',
    chatPlaceholder: 'Ställ en fråga…',
    chatEmpty: 'Ställ en analysfråga, t.ex. "Visa mina topprodukter"',
    chatThinking: 'Tänker…',
    chatSend: 'Skicka',
    chatError: 'Förfrågan misslyckades. Försök igen.',
    newConversation: 'Ny konversation',
    chatSuggestions: [
      'Varför förändrades försäljningen under perioden?',
      'Vilka butiker underpresterar?',
      'Jämför onlineförsäljning med fysiska butiker.',
      'Vilka produkter drev resultatet?',
    ],
    chatContext: (dateFrom, dateTo) => `${dateFrom} – ${dateTo}`,
    explainWithAi: 'Förklara med AI',
    explainKpi: (metricLabel) =>
      `Förklara förändringen i ${metricLabel} för den aktuella perioden.`,
    explainTrend: (metricLabel) =>
      `Analysera trenden för ${metricLabel} i den aktuella dashboardvyn. Vad sticker ut?`,
    explainPerformance: (metricLabel, groupLabel) =>
      `Analysera ${metricLabel} per ${groupLabel.toLowerCase()} i den aktuella dashboardvyn. Vad sticker ut?`,
    loading: 'Laddar…',
    noProducts: 'Inga produkter hittades.',
    colProduct: 'Produkt',
    colCategory: 'Kategori',
    sortBy: (label) => `Sortera efter ${label}`,
    loadingMoreProducts: 'Laddar fler produkter…',
    productsLoaded: (loaded, total) => `${loaded} av ${total} produkter`,
    grain: 'Granularitet',
    grainMonth: 'Månad',
    grainWeek: 'Vecka',
    metric: 'Mätvärde',
    productsSelected: (n) => `Produkter (${n} valda)`,
    productsTop5: 'Produkter (topp 5)',
    clearSelection: 'Rensa',
    productsNoneSelected: 'Produkter (inga valda)',
    noTimeseriesData: 'Ingen tidsseriedata tillgänglig.',
    noStoreData: 'Ingen butiksdata tillgänglig.',
    noPerformanceTrendData: 'Ingen trenddata för prestationen tillgänglig.',
    view: 'Vy',
    ranking: 'Rankning',
    trend: 'Trend',
    addComparison: 'Lägg till jämförelse',
    removeComparison: 'Ta bort jämförelse',
    currentPeriod: 'Aktuell period',
    previousPeriod: 'Föregående period',
    vizNoMetrics: 'Inga mätvärden att visa.',
    vizNoChartData: 'Ingen giltig data att visualisera.',
    vizNoRows: 'Inga rader att visa.',
    vizNoValidColumns: 'Inga giltiga tabellkolumner angavs.',
    vizUnsupported: 'Visualiseringstypen stöds inte.',
    vizRenderError: 'Visualiseringen kunde inte renderas.',
    rankedBy: 'Rangordnad efter',
    rankingMetric: 'Rankningsmått',
    export: 'Exportera',
    exporting: 'Exporterar…',
    exportExcel: 'Excel (.xlsx)',
    exportCsv: 'CSV (.csv)',
    exportPng: 'PNG-bild',
    exportFailed: 'Exporten misslyckades.',
    exportDataSheet: 'Data',
    exportFiltersSheet: 'Filter',
    exportFilter: 'Filter',
    exportValue: 'Värde',
    salesSummary: 'Försäljningsöversikt',
    vsPreviousPeriod: 'mot föregående period',
    exportTopProducts: 'Topp 5 produkter',
    exportSortedBy: 'Sorterat efter',
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
    value: 'Value',
    period_end: 'Period end',
    group_by: 'Group by',
    rank_by: 'Rank by',
    split_by: 'Split by',
    grain: 'Grain',
    limit: 'Limit',
    series_limit: 'Series limit',
    order: 'Order',
    channels: 'Channels',
    cities: 'Cities',
    store_ids: 'Stores',
    categories: 'Categories',
    product_ids: 'Products',
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
    value: 'Värde',
    period_end: 'Periodslut',
    group_by: 'Gruppera efter',
    rank_by: 'Rangordna efter',
    split_by: 'Dela upp efter',
    grain: 'Granularitet',
    limit: 'Antal',
    series_limit: 'Max antal serier',
    order: 'Ordning',
    channels: 'Kanaler',
    cities: 'Städer',
    store_ids: 'Butiker',
    categories: 'Kategorier',
    product_ids: 'Produkter',
  },
}

const visualizationValueLabels: Record<Language, Record<string, string>> = {
  en: {
    online: 'Online',
    physical: 'Physical',
    day: 'Day',
    week: 'Week',
    month: 'Month',
    quarter: 'Quarter',
    product: 'Product',
    category: 'Category',
    store: 'Store',
    city: 'City',
    channel: 'Channel',
    highest: 'Highest',
    lowest: 'Lowest',
  },
  sv: {
    online: 'Online',
    physical: 'Fysisk',
    day: 'Dag',
    week: 'Vecka',
    month: 'Månad',
    quarter: 'Kvartal',
    product: 'Produkt',
    category: 'Kategori',
    store: 'Butik',
    city: 'Stad',
    channel: 'Kanal',
    highest: 'Högst',
    lowest: 'Lägst',
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
