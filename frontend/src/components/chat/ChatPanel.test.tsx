import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ChatPanel } from './ChatPanel'
import { LanguageProvider } from '../../i18n/LanguageContext'
import type { AgentQueryResponse } from '../../types/agent'

function renderChat() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <LanguageProvider>
        <ChatPanel />
      </LanguageProvider>
    </QueryClientProvider>,
  )
}

function okResponse(data: AgentQueryResponse) {
  return { ok: true, status: 200, json: async () => data, text: async () => '' } as Response
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
  datasets: [],
  visualizations: [],
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

  it('New conversation clears conversation_id', async () => {
    renderChat()
    submit('turn 1')
    await screen.findByText('Winner is Hoodie.')
    fireEvent.click(screen.getByRole('button', { name: /konversation|conversation/i }))
    submit('fresh start')
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2))
    const body = JSON.parse(fetchMock.mock.calls[1][1].body)
    expect(body.conversation_id).toBeNull()
  })

  it('renders assistant text and visualizations from the response', async () => {
    fetchMock.mockResolvedValueOnce(
      okResponse({
        ...baseResponse,
        message: 'Here is the ranking.',
        datasets: [
          { call_id: 'c1', tool_name: 'sales_rank', status: 'success', result: { rows: [{ entity: { name: 'Hoodie' }, metrics: { units: 40 } }] } },
        ],
        visualizations: [{ dataset: 'c1', type: 'bar_chart', title: 'Top products', y_keys: ['units'] }],
      }),
    )
    renderChat()
    submit('rank')
    expect(await screen.findByText('Here is the ranking.')).toBeInTheDocument()
    expect(screen.getByText('Top products')).toBeInTheDocument()
  })

  it('shows an error state when the request fails', async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, status: 500, text: async () => 'boom' } as Response)
    renderChat()
    submit('will fail')
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })

  it('prevents duplicate submission while a request is in flight', async () => {
    let resolveFetch: (r: Response) => void = () => {}
    fetchMock.mockImplementationOnce(() => new Promise<Response>((r) => { resolveFetch = r }))
    renderChat()
    submit('slow one')
    const input = screen.getByRole('textbox') as HTMLInputElement
    await waitFor(() => expect(input).toBeDisabled())
    // Attempt a second submit while pending.
    fireEvent.submit(input.closest('form')!)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    resolveFetch(okResponse(baseResponse))
    await screen.findByText('Winner is Hoodie.')
  })
})
