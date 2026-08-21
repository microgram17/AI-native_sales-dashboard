import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { LanguageProvider } from '../../../i18n/LanguageContext'
import type { TopProductsRow } from '../../../types/dashboard'
import { TopProductsTable } from './TopProductsTable'

const rows: TopProductsRow[] = [
  {
    rank: 1,
    product_id: 'P-1',
    product_name: 'Product 1',
    category: 'Test',
    net_sales: 100,
    gross_sales: 120,
    units: 4,
    orders: 3,
    discounts: 20,
  },
]

afterEach(cleanup)

function renderTable(overrides: Partial<React.ComponentProps<typeof TopProductsTable>> = {}) {
  const props: React.ComponentProps<typeof TopProductsTable> = {
    rows,
    loading: false,
    sortBy: 'net_sales',
    sortDirection: 'desc',
    onSortChange: vi.fn(),
    hasMore: true,
    loadingMore: false,
    total: 72,
    onLoadMore: vi.fn(),
    ...overrides,
  }

  const result = render(
    <LanguageProvider>
      <TopProductsTable {...props} />
    </LanguageProvider>,
  )
  return { ...result, props }
}

describe('TopProductsTable', () => {
  it('sorts by the selected metric header', () => {
    const { props } = renderTable()

    fireEvent.click(
      screen.getByRole('button', { name: /bruttoomsättning/i }),
    )

    expect(props.onSortChange).toHaveBeenCalledWith('gross_sales', 'desc')
  })

  it('reverses the direction when the selected metric is clicked again', () => {
    const { props, getByRole } = renderTable({
      sortBy: 'units',
      sortDirection: 'desc',
    })

    fireEvent.click(
      getByRole('button', { name: /^enheter/i }),
    )

    expect(props.onSortChange).toHaveBeenCalledWith('units', 'asc')
    expect(
      getByRole('columnheader', { name: /enheter/i }),
    ).toHaveAttribute('aria-sort', 'descending')
  })

  it('loads the next page when its internal viewport nears the bottom', () => {
    const { container, props } = renderTable()
    const viewport = container.querySelector('.top-products-table-scroll')!
    Object.defineProperties(viewport, {
      scrollHeight: { value: 800 },
      clientHeight: { value: 380 },
      scrollTop: { value: 360, writable: true },
    })

    fireEvent.scroll(viewport)

    expect(props.onLoadMore).toHaveBeenCalledOnce()
  })
})
