import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import ChatPage from './pages/ChatPage'
import ActivityPage from './pages/ActivityPage'
import SourcesPage from './pages/SourcesPage'
import EvaluationsPage from './pages/EvaluationsPage'
import SettingsPage from './pages/SettingsPage'
import LoginPage from './pages/LoginPage'
import { hasToken } from './lib/auth'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  if (!hasToken()) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<HomePage />} />
          <Route path="chat" element={<ChatPage />} />
          <Route path="chat/:id" element={<ChatPage />} />
          <Route path="activity" element={<ActivityPage />} />
          <Route path="sources" element={<SourcesPage />} />
          <Route path="connections" element={<SourcesPage />} />
          <Route path="evaluations" element={<EvaluationsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}