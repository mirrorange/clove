import axios from 'axios'
import { toast } from 'sonner'
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

// 添加请求拦截器以添加 admin key
api.interceptors.request.use(config => {
    const adminKey = localStorage.getItem('adminKey')
    if (adminKey) {
        config.headers['X-API-Key'] = adminKey
    }
    return config
})

// 添加响应拦截器以处理全局错误
api.interceptors.response.use(
    response => response,
    error => {
        // 处理登录失效
        if (error.response?.data?.detail?.code === 401011) {
            localStorage.removeItem('adminKey')
            if (window.location.pathname !== '/login') {
                window.location.href = '/login'
            }
            return Promise.reject(error)
        }

        // 尝试获取错误响应中的 detail.message
        const errorMessage = error.response?.data?.detail?.message || '发生未知错误'

        toast.error(errorMessage)

        // 继续抛出错误，以便组件层可以进一步处理
        return Promise.reject(error)
    },
)

// 账户相关 API
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

// 设置相关 API
export const settingsApi = {
    get: () => api.get<SettingsRead>('/api/admin/settings'),
    update: (settings: SettingsUpdate) => api.put<SettingsUpdate>('/api/admin/settings', settings),
}

// 健康检查
export const healthApi = {
    check: () => api.get('/health'),
}

// 统计信息 API
export const statisticsApi = {
    get: () => api.get<StatisticsResponse>('/api/admin/statistics'),
}
