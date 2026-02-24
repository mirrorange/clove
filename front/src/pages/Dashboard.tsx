import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Users, Settings, Activity, Server } from 'lucide-react'
import { healthApi, statisticsApi } from '../api/client'
import type { StatisticsResponse } from '../api/types'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'

export function Dashboard() {
    const { t } = useTranslation()
    const [statistics, setStatistics] = useState<StatisticsResponse | null>(null)
    const [serverStatus, setServerStatus] = useState<'online' | 'offline'>('offline')
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const loadData = async () => {
            try {
                const [statsRes, healthRes] = await Promise.all([statisticsApi.get(), healthApi.check()])

                setStatistics(statsRes.data)
                setServerStatus(healthRes.status === 200 ? 'online' : 'offline')
            } catch (error) {
                console.error('Failed to load dashboard data:', error)
                setServerStatus('offline')
            } finally {
                setLoading(false)
            }
        }

        loadData()
    }, [])

    const stats = [
        {
            name: t('dashboard.totalAccounts'),
            value: serverStatus === 'offline' ? 'N/A' : (statistics?.accounts.total_accounts ?? 0).toString(),
            icon: Users,
            color: 'text-pink-500',
            bgColor: 'bg-pink-50',
        },
        {
            name: t('dashboard.serverStatus'),
            value: serverStatus === 'online' ? t('dashboard.online') : t('dashboard.offline'),
            icon: Server,
            color: serverStatus === 'online' ? 'text-green-500' : 'text-red-500',
            bgColor: serverStatus === 'online' ? 'bg-green-50' : 'bg-red-50',
        },
        {
            name: t('dashboard.activeSessions'),
            value: serverStatus === 'offline' ? 'N/A' : (statistics?.accounts.active_sessions ?? 0).toString(),
            icon: Activity,
            color: 'text-blue-500',
            bgColor: 'bg-blue-50',
        },
        {
            name: t('dashboard.systemStatus'),
            value: serverStatus === 'offline' ? 'N/A' : statistics?.status === 'healthy' ? t('dashboard.normal') : t('dashboard.degraded'),
            icon: Settings,
            color: statistics?.status === 'healthy' ? 'text-green-500' : 'text-yellow-500',
            bgColor: statistics?.status === 'healthy' ? 'bg-green-50' : 'bg-yellow-50',
        },
    ]

    if (loading) {
        return (
            <div className='space-y-6'>
                <div className='space-y-2'>
                    <Skeleton className='h-8 w-32' />
                    <Skeleton className='h-4 w-64' />
                </div>

                <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
                    {[...Array(4)].map((_, i) => (
                        <Card key={i}>
                            <CardHeader className='flex flex-row items-center justify-between space-y-0 pb-1'>
                                <Skeleton className='h-4 w-24' />
                                <Skeleton className='h-12 w-12 rounded-full' />
                            </CardHeader>
                            <CardContent>
                                <Skeleton className='h-7 w-16' />
                            </CardContent>
                        </Card>
                    ))}
                </div>
            </div>
        )
    }

    return (
        <div className='space-y-6'>
            <div>
                <h1 className='text-3xl font-bold tracking-tight pb-1'>{t('dashboard.title')}</h1>
                <p className='text-muted-foreground'>{t('dashboard.welcome')}</p>
            </div>

            <div className='grid gap-4 md:grid-cols-2 lg:grid-cols-4'>
                {stats.map(item => (
                    <Card key={item.name} className='hover:shadow-lg transition-shadow gap-1 py-4'>
                        <CardHeader className='flex flex-row items-center justify-between space-y-0'>
                            <CardTitle className='text-md font-medium text-muted-foreground'>{item.name}</CardTitle>
                            <div className={`p-3 rounded-full ${item.bgColor}`}>
                                <item.icon className={`h-6 w-6 ${item.color}`} />
                            </div>
                        </CardHeader>
                        <CardContent>
                            <div className='text-2xl font-bold'>{item.value}</div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <div>
                <h2 className='text-2xl font-semibold mb-4'>{t('dashboard.quickActions')}</h2>
                <div className='grid gap-4 md:grid-cols-2'>
                    <Card className='hover:shadow-lg transition-all hover:border-primary/50'>
                        <CardHeader>
                            <div className='flex items-center space-x-4'>
                                <div className='p-3 rounded-lg bg-pink-50'>
                                    <Users className='h-6 w-6 text-pink-500' />
                                </div>
                                <div className='space-y-1'>
                                    <CardTitle>{t('dashboard.manageAccounts')}</CardTitle>
                                    <CardDescription>{t('dashboard.manageAccountsDesc')}</CardDescription>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <Button asChild className='w-full'>
                                <Link to='/accounts'>{t('dashboard.goToAccounts')}</Link>
                            </Button>
                        </CardContent>
                    </Card>

                    <Card className='hover:shadow-lg transition-all hover:border-primary/50'>
                        <CardHeader>
                            <div className='flex items-center space-x-4'>
                                <div className='p-3 rounded-lg bg-purple-50'>
                                    <Settings className='h-6 w-6 text-purple-500' />
                                </div>
                                <div className='space-y-1'>
                                    <CardTitle>{t('dashboard.systemSettings')}</CardTitle>
                                    <CardDescription>{t('dashboard.systemSettingsDesc')}</CardDescription>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <Button asChild variant='secondary' className='w-full'>
                                <Link to='/settings'>{t('dashboard.goToSettings')}</Link>
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    )
}
