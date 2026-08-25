import { useState, type FormEvent } from 'react'

import { ApiError } from '../../api/client'
import { useTranslation } from '../../i18n/LanguageContext'
import {
  RetailerAdminUiNotImplementedError,
  useAuth,
} from './AuthContext'


export function LoginPage() {
  const { t } = useTranslation()
  const { login } = useAuth()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!email.trim() || !password || submitting) return

    setSubmitting(true)
    setError(null)

    try {
      await login(email, password)
    } catch (caught) {
      if (caught instanceof RetailerAdminUiNotImplementedError) {
        setError(t.loginAdminNotAvailable)
      } else if (caught instanceof ApiError && caught.status === 401) {
        setError(t.loginInvalidCredentials)
      } else {
        setError(t.loginError)
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-heading">
          <div className="login-eyebrow">Supplier BI</div>
          <h1>{t.loginTitle}</h1>
          <p>{t.loginSubtitle}</p>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            <span>{t.loginEmail}</span>
            <input
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={submitting}
              required
            />
          </label>

          <label>
            <span>{t.loginPassword}</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={submitting}
              required
            />
          </label>

          {error && (
            <div className="login-error" role="alert">
              {error}
            </div>
          )}

          <button
            className="login-submit"
            type="submit"
            disabled={submitting || !email.trim() || !password}
          >
            {submitting ? t.loginSigningIn : t.loginButton}
          </button>
        </form>
      </section>
    </main>
  )
}
