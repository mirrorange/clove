import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { KeyRound, Loader2 } from 'lucide-react'
import { statisticsApi } from '../api/client'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'

export function Login() {
    const { t } = useTranslation()
    const [adminKey, setAdminKey] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const navigate = useNavigate()

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setError('')
        setLoading(true)

        try {
            // Save admin key
            localStorage.setItem('adminKey', adminKey)

            // Verify Admin Key via statistics API
            await statisticsApi.get()

            // Redirect on success
            navigate('/')
        } catch (err) {
            setError(t('login.invalidKey'))
            localStorage.removeItem('adminKey')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-pink-50 via-white to-purple-50 relative overflow-hidden">
            {/* Decorative background elements */}
            <div className="absolute inset-0 opacity-30">
                <div className="absolute top-10 left-10 w-72 h-72 bg-pink-200 rounded-full filter blur-3xl animate-pulse"></div>
                <div className="absolute bottom-10 right-10 w-96 h-96 bg-purple-200 rounded-full filter blur-3xl animate-pulse animation-delay-2000"></div>
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-pink-100 rounded-full filter blur-3xl animate-pulse animation-delay-4000"></div>
            </div>
            
            <Card className="w-full max-w-md relative z-10 shadow-xl border-0 backdrop-blur-sm bg-white/95">
                <CardHeader className="space-y-1 text-center">
                    <div className="flex justify-center mb-4">
                        <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-pink-500 to-purple-500 flex items-center justify-center shadow-lg">
                            <span className="text-3xl font-bold text-white">C</span>
                        </div>
                    </div>
                    <CardTitle className="text-2xl font-bold">{t('login.welcomeBack')}</CardTitle>
                    <CardDescription>
                        {t('login.subtitle')}
                    </CardDescription>
                </CardHeader>
                
                <form onSubmit={handleSubmit}>
                    <CardContent className="space-y-4 pb-4">
                        <div className="space-y-2">
                            <Label htmlFor="admin-key">Admin Key</Label>
                            <div className="relative">
                                <KeyRound className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                                <Input
                                    id="admin-key"
                                    type="password"
                                    placeholder={t('login.placeholder')}
                                    value={adminKey}
                                    onChange={(e) => setAdminKey(e.target.value)}
                                    className="pl-10"
                                    required
                                />
                            </div>
                        </div>

                        {error && (
                            <Alert variant="destructive">
                                <AlertDescription>{error}</AlertDescription>
                            </Alert>
                        )}
                    </CardContent>
                    
                    <CardFooter>
                        <Button
                            type="submit"
                            className="w-full"
                            disabled={loading || !adminKey.trim()}
                        >
                            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            {loading ? t('login.verifying') : t('login.signIn')}
                        </Button>
                    </CardFooter>
                </form>
            </Card>
            
            <div className="absolute bottom-4 left-0 right-0 text-center text-sm text-muted-foreground">
                <p>{t('login.footer')}</p>
            </div>
        </div>
    )
}
