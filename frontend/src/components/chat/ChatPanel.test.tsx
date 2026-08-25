import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChatPanel } from './ChatPanel'
import { LanguageProvider } from '../../i18n/LanguageContext'
import type { AgentQueryResponse } from '../../types/agent'

function renderChat(
  props?: React.ComponentProps<typeof ChatPanel>,
) {
  const client = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
      queries: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={client}>
      <LanguageProvider>
        <ChatPanel {...props} />
      </LanguageProvider>
    </QueryClientProvider>,
  )
}

function okResponse(data: AgentQueryResponse) {
  return {
    ok: true,
    status: 200,
    json: async () => data,
    text: async () => '',
  } as Response
}

function submit(text: string) {
  const input = screen.getByRole('textbox') as HTMLInputElement
  fireEvent.change(input, { target: { value: text } })
  fireEvent.submit(input.closest('form')!)
}

const baseResponse: AgentQueryResponse = {
  conversation_id: 'conv-1',
  message: 'Winner is Hoodie.',
  tool_calls: [],
  data_context: null,
  data_views: [],
  displays: [],
}

let fetchMock: ReturnType<typeof vi.fn>

beforeEach(() => {
  fetchMock = vi.fn().mockResolvedValue(okResponse(baseResponse))
  vi.stubGlobal('fetch', fetchMock)
})

afterEach(() => {
  cleanup()
  vi.unstubAllGlobals()
})

describe('ChatPanel', () => {
  it('renders assistant Markdown without enabling raw HTML', async () => {
    fetchMock.mockResolvedValue(okResponse({
      ...baseResponse,
      message: [
        '**Important result**',
        '',
        '- First observation',
        '- Second observation',
        '',
        '[Details](https://example.com)',
        '![Generated chart](data:image/png;base64,unsafe)',
        '<script>unsafe()</script>',
      ].join('\n'),
    }))

    renderChat()
    submit('analyze')

    const strong = await screen.findByText('Important result')
    expect(strong.tagName).toBe('STRONG')
    expect(screen.getAllByRole('listitem')).toHaveLength(2)
    const link = screen.getByRole('link', { name: 'Details' })
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noreferrer noopener')
    expect(document.querySelector('script')).toBeNull()
    expect(document.querySelector('img')).toBeNull()
    expect(screen.queryByText('unsafe()')).not.toBeInTheDocument()
  })

  it('submits to POST /agent/query without supplier and with null conversation_id first', async () => {
    renderChat()
    submit('best product?')
    await screen.findByText('Winner is Hoodie.')

    const [url, init] = fetchMock.mock.calls[0]
    expect(String(url)).toContain('/agent/query')
    expect(init.method).toBe('POST')

    const body = JSON.parse(init.body)
    expect(body.message).toBe('best product?')
    expect(body.conversation_id).toBeNull()
    expect(body.language).toBe('sv')
    expect(body).not.toHaveProperty('supplier_id')
    expect(body).not.toHaveProperty('supplier_code')
  })

  it('reuses the returned conversation_id on the next message', async () => {
    renderChat()
    submit('turn 1')
    await screen.findByText('Winner is Hoodie.')
    submit('turn 2')

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    const secondBody = JSON.parse(fetchMock.mock.calls[1][1].body)
    expect(secondBody.conversation_id).toBe('conv-1')
  })

  it('sends the active dashboard context with a question', async () => {
    renderChat({
      dashboardContext: {
        date_from: '2026-01-01',
        date_to: '2026-06-30',
        metric: 'net_sales',
        group_by: 'store',
      },
    })
    submit('what stands out?')

    await screen.findByText('Winner is Hoodie.')
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.dashboard_context).toEqual({
      date_from: '2026-01-01',
      date_to: '2026-06-30',
      metric: 'net_sales',
      group_by: 'store',
    })
  })

  it('uses a suggested question to populate the composer', () => {
    renderChat()

    fireEvent.click(
      screen.getByRole('button', {
        name: /förändrades försäljningen/i,
      }),
    )

    expect(screen.getByRole('textbox')).toHaveValue(
      'Varför förändrades försäljningen under perioden?',
    )
  })

  it('starts and submits a fresh widget-scoped analysis automatically', async () => {
    renderChat({
      requestedPrompt: {
        id: 1,
        text: 'Analyze this trend.',
        widgetAnalysis: {
          widget: 'sales_trend',
          operation: 'trend',
          metrics: ['net_sales'],
          period_start: '2026-01-01',
          period_end: '2026-06-30',
          grain: 'month',
        },
      },
    })

    await screen.findByText('Winner is Hoodie.')
    const body = JSON.parse(fetchMock.mock.calls[0][1].body)
    expect(body.conversation_id).toBeNull()
    expect(body.widget_analysis).toEqual({
      widget: 'sales_trend',
      operation: 'trend',
      metrics: ['net_sales'],
      period_start: '2026-01-01',
      period_end: '2026-06-30',
      grain: 'month',
    })
    expect(screen.getByText('Analyze this trend.')).toBeInTheDocument()
  })

  it('New conversation clears conversation_id', async () => {
    renderChat()
    submit('turn 1')
    await screen.findByText('Winner is Hoodie.')

    fireEvent.click(
      screen.getByRole('button', { name: /konversation|conversation/i }),
    )
    submit('fresh start')

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    const body = JSON.parse(fetchMock.mock.calls[1][1].body)
    expect(body.conversation_id).toBeNull()
  })

  it('renders assistant text and semantic data views from the response', async () => {
    fetchMock.mockResolvedValueOnce(
      okResponse({
        ...baseResponse,
        message: 'Here is the ranking.',
        data_context: {
          operation: 'ranking',
          effective_period: {
            start: '2026-01-01',
            end: '2026-03-31',
            label: 'Q1 2026',
            defaulted: false,
          },
          effective_scope: {},
          group_by: 'product',
          rank_by: 'units',
          order: 'highest',
        },
        data_views: [
          {
            id: 'ranking',
            kind: 'categorical',
            rows: [{ entity_name: 'Hoodie', units: 40 }],
            fields: [
              { key: 'entity_name', role: 'dimension', format: 'text' },
              { key: 'units', role: 'measure', format: 'integer' },
            ],
            primary_dimension: 'entity_name',
            default_measures: ['units'],
            default_visible: true,
          },
        ],
        displays: [
          {
            view_id: 'ranking',
            render_as: 'default',
            measure_keys: ['units'],
            title: 'Top products',
          },
        ],
      }),
    )

    renderChat()
    submit('rank')

    const assistantText = await screen.findByText('Here is the ranking.')
    const visualizationTitle = screen.getByText('Top products')

    expect(assistantText).toBeInTheDocument()
    expect(visualizationTitle).toBeInTheDocument()
    expect(
      assistantText.closest('.message-bubble'),
    ).toBe(
      visualizationTitle.closest('.message-bubble'),
    )
  })

  it('shows an error state when the request fails', async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: async () => 'boom',
    } as Response)

    renderChat()
    submit('will fail')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('prevents duplicate submission while a request is in flight', async () => {
    let resolveFetch: (r: Response) => void = () => {}

    fetchMock.mockImplementationOnce(
      () =>
        new Promise<Response>((resolve) => {
          resolveFetch = resolve
        }),
    )

    renderChat()
    submit('slow one')

    const input = screen.getByRole('textbox') as HTMLInputElement
    await waitFor(() => expect(input).toBeDisabled())

    fireEvent.submit(input.closest('form')!)
    expect(fetchMock).toHaveBeenCalledTimes(1)

    resolveFetch(okResponse(baseResponse))
    await screen.findByText('Winner is Hoodie.')
  })
})
