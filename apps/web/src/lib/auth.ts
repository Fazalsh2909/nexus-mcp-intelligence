const TOKEN_KEY = 'nexus_token'
const LOGGED_OUT_KEY = 'nexus_logged_out'

export function hasToken(): boolean {
  return !!localStorage.getItem(TOKEN_KEY)
}

export function markLoggedOut() {
  localStorage.setItem(LOGGED_OUT_KEY, '1')
  localStorage.removeItem('nexus_last_session')
}

export function clearLoggedOutFlag() {
  localStorage.removeItem(LOGGED_OUT_KEY)
}