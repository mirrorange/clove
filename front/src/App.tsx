import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Dashboard } from './pages/Dashboard'
import { Accounts } from './pages/Accounts'
import { Settings } from './pages/Settings'
import { Toaster } from './components/ui/sonner'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const adminKey = localStorage.getItem('adminKey')
    if (!adminKey) {
        return <Navigate to='/login' replace />
    }
    return <>{children}</>
}

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path='/login' element={<Login />} />
                <Route
                    path='/'
                    element={
                        <ProtectedRoute>
                            <Layout />
                        </ProtectedRoute>
                    }
                >
                    <Route index element={<Dashboard />} />
                    <Route path='accounts' element={<Accounts />} />
                    <Route path='settings' element={<Settings />} />
                </Route>
            </Routes>
            <Toaster />
        </BrowserRouter>
    )
}

export default App
