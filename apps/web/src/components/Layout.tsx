import { useEffect, useState } from 'react'
import { Outlet, useNavigate } from 'react-router-dom'
import { AppSidebar } from './AppSidebar'
import { Topbar } from './Topbar'
import { CommandPalette } from './CommandPalette'
import { WorkspaceProvider } from '../lib/workspace'
import { markLoggedOut } from '../lib/auth'

function Shell() {
  const navigate = useNavigate()
  const [paletteOpen, setPaletteOpen] = useState(false)

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setPaletteOpen(open => !open)
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  const logout = () => {
    localStorage.removeItem('nexus_token')
    markLoggedOut()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <AppSidebar onLogout={logout} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar onOpenPalette={() => setPaletteOpen(true)} />
        <main className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <Outlet />
        </main>
      </div>
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} />
    </div>
  )
}

export default function Layout() {
  return (
    <WorkspaceProvider>
      <Shell />
    </WorkspaceProvider>
  )
}