import axios from 'axios'
import { toast } from 'sonner'
import i18n from '../i18n/i18n-config'
import type {
    AccountResponse,
    AccountCreate,
    AccountUpdate,
    OAuthCodeExchange,
    SettingsRead,
    SettingsUpdate,
    StatisticsResponse,
} from './types'

const api = axios.create({
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor to attach admin key from local storage
api.interceptors.request.use(config => {
    const adminKey = localStorage.getItem('adminKey')
    if (adminKey) {
        config.headers['X-API-Key'] = adminKey
    }
    return config
})

// Response interceptor to handle global errors
api.interceptors.response.use(
    response => response,
    error => {
        // Handle session expiry - redirect to login
        if (error.response?.data?.detail?.code === 401011) {
            localStorage.removeItem('adminKey')
            if (window.location.pathname !== '/login') {
                window.location.href = '/login'
            }
            return Promise.reject(error)
        }

        // Attempt to extract error message from detail.message field
        const errorMessage = error.response?.data?.detail?.message || i18n.t('common.unknownError')

        toast.error(errorMessage)

        // Re-throw error so component layer can handle it further
        return Promise.reject(error)
    },
)

// Account-related API
export const accountsApi = {
    list: () => api.get<AccountResponse[]>('/api/admin/accounts'),
    get: (organizationUuid: string) => api.get<AccountResponse>(`/api/admin/accounts/${organizationUuid}`),
    create: (account: AccountCreate) => api.post<AccountResponse>('/api/admin/accounts', account),
    update: (organizationUuid: string, account: AccountUpdate) =>
        api.put<AccountResponse>(`/api/admin/accounts/${organizationUuid}`, account),
    delete: (organizationUuid: string) => api.delete(`/api/admin/accounts/${organizationUuid}`),
    exchangeOAuthCode: (exchangeData: OAuthCodeExchange) =>
        api.post<AccountResponse>('/api/admin/accounts/oauth/exchange', exchangeData),
}

// Settings-related API
export const settingsApi = {
    get: () => api.get<SettingsRead>('/api/admin/settings'),
    update: (settings: SettingsUpdate) => api.put<SettingsUpdate>('/api/admin/settings', settings),
}

// Health check
export const healthApi = {
    check: () => api.get('/health'),
}

// Statistics API
export const statisticsApi = {
    get: () => api.get<StatisticsResponse>('/api/admin/statistics'),
}
