import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, AlertCircle, CheckCircle, Cookie, FileText, Copy, Check } from 'lucide-react'
import { accountsApi } from '../api/client'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from '@/components/ui/drawer'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { useIsMobile } from '@/hooks/use-mobile'
import { toast } from 'sonner'
import type { AccountCreate } from '../api/types'

interface BatchCookieModalProps {
    onClose: () => void
}

interface CookieResult {
    cookie: string
    status: 'pending' | 'processing' | 'success' | 'error'
    error?: string
    organizationUuid?: string
}

export function BatchCookieModal({ onClose }: BatchCookieModalProps) {
    const { t } = useTranslation()
    const [cookies, setCookies] = useState('')
    const [isProcessing, setIsProcessing] = useState(false)
    const [results, setResults] = useState<CookieResult[]>([])
    const [showResults, setShowResults] = useState(false)
    const isMobile = useIsMobile()

    const validateAndProcessCookie = (cookieValue: string): { isValid: boolean; processedValue: string } => {
        let processedValue = cookieValue.trim()

        if (processedValue.startsWith('sk-ant-sid01-')) {
            processedValue = `sessionKey=${processedValue}`
        }

        const isValid = processedValue.startsWith('sessionKey=sk-ant-sid01-')

        return { isValid, processedValue }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        const cookieLines = cookies
            .split('\n')
            .map(line => line.trim())
            .filter(line => line.length > 0)

        if (cookieLines.length === 0) {
            return
        }

        setIsProcessing(true)
        setShowResults(true)

        const initialResults: CookieResult[] = cookieLines.map(cookie => ({
            cookie,
            status: 'pending',
        }))
        setResults(initialResults)

        for (let i = 0; i < cookieLines.length; i++) {
            const cookie = cookieLines[i]

            setResults(prev => {
                const updated = [...prev]
                updated[i] = { ...updated[i], status: 'processing' }
                return updated
            })

            try {
                const { isValid, processedValue } = validateAndProcessCookie(cookie)

                if (!isValid) {
                    setResults(prev => {
                        const updated = [...prev]
                        updated[i] = {
                            ...updated[i],
                            status: 'error',
                            error: t('batchModal.invalidFormat'),
                        }
                        return updated
                    })
                    continue
                }

                const createData: AccountCreate = {
                    cookie_value: processedValue,
                }

                const response = await accountsApi.create(createData)

                setResults(prev => {
                    const updated = [...prev]
                    updated[i] = {
                        ...updated[i],
                        status: 'success',
                        organizationUuid: response.data.organization_uuid,
                    }
                    return updated
                })
            } catch (error: any) {
                const errorMessage = error.response?.data?.detail?.message || t('batchModal.addFailed')

                setResults(prev => {
                    const updated = [...prev]
                    updated[i] = {
                        ...updated[i],
                        status: 'error',
                        error: errorMessage,
                    }
                    return updated
                })
            }

            // Small delay to avoid rate limiting
            await new Promise(resolve => setTimeout(resolve, 300))
        }

        setIsProcessing(false)
    }

    const getProgress = () => {
        if (results.length === 0) return 0
        const processed = results.filter(r => r.status === 'success' || r.status === 'error').length
        return (processed / results.length) * 100
    }

    const getSuccessCount = () => results.filter(r => r.status === 'success').length
    const getErrorCount = () => results.filter(r => r.status === 'error').length

    const copyFailedCookies = async () => {
        const failedCookies = results
            .filter(r => r.status === 'error')
            .map(r => r.cookie)
            .join('\n')

        try {
            await navigator.clipboard.writeText(failedCookies)
            toast.success(t('batchModal.copiedFailed'), {
                icon: <Check className='h-4 w-4' />,
            })
        } catch (error) {
            console.error('Failed to copy:', error)
            toast.error(t('common.copyFailed'))
        }
    }

    const truncateCookie = (cookie: string, maxLength: number = 40) => {
        if (cookie.length <= maxLength) return cookie
        const start = cookie.substring(0, 20)
        const end = cookie.substring(cookie.length - 17)
        return `${start}...${end}`
    }

    const getStatusIcon = (status: CookieResult['status']) => {
        switch (status) {
            case 'success':
                return <CheckCircle className='h-4 w-4 text-green-500' />
            case 'error':
                return <AlertCircle className='h-4 w-4 text-red-500' />
            case 'processing':
                return <Loader2 className='h-4 w-4 animate-spin' />
            default:
                return <Cookie className='h-4 w-4 text-muted-foreground' />
        }
    }

    const handleClose = () => {
        if (isProcessing) return
        onClose()
    }

    const formContent = (
        <>
            {!showResults ? (
                <>
                    <div className='space-y-2'>
                        <Label htmlFor='cookies'>
                            {t('batchModal.cookieList')} <span className='text-destructive'>*</span>
                        </Label>
                        <Textarea
                            id='cookies'
                            placeholder={t('batchModal.placeholder')}
                            value={cookies}
                            onChange={e => setCookies(e.target.value)}
                            className='min-h-[200px] font-mono text-sm break-all'
                            required
                        />
                        <p className='text-sm text-muted-foreground'>{t('batchModal.supportedFormats')}</p>
                    </div>
                </>
            ) : (
                <div className='space-y-4'>
                    <div className='space-y-2'>
                        <div className='flex items-center justify-between'>
                            <Label>{t('batchModal.progress')}</Label>
                            <span className='text-sm text-muted-foreground'>
                                {t('batchModal.successCount', { success: getSuccessCount(), error: getErrorCount(), total: results.length })}
                            </span>
                        </div>
                        <Progress value={getProgress()} className='h-2' />
                    </div>

                    <div className='border rounded-lg max-h-[300px] overflow-y-auto'>
                        <div className='divide-y'>
                            {results.map((result, index) => (
                                <div key={index} className='p-3 flex items-start gap-3'>
                                    <div className='mt-0.5'>{getStatusIcon(result.status)}</div>
                                    <div className='flex-1 min-w-0'>
                                        <p className='font-mono text-xs' title={result.cookie}>
                                            {truncateCookie(result.cookie)}
                                        </p>
                                        {result.status === 'success' && result.organizationUuid && (
                                            <p className='text-xs text-muted-foreground mt-1'>
                                                UUID: {result.organizationUuid}
                                            </p>
                                        )}
                                        {result.status === 'error' && result.error && (
                                            <p className='text-xs text-destructive mt-1 break-words'>{result.error}</p>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {!isProcessing && (
                        <>
                            <Alert>
                                <FileText className='h-4 w-4' />
                                <AlertDescription>
                                    {getErrorCount() > 0
                                        ? t('batchModal.completeMessageWithErrors', { success: getSuccessCount(), error: getErrorCount() })
                                        : t('batchModal.completeMessage', { count: getSuccessCount() })}
                                </AlertDescription>
                            </Alert>
                            {getErrorCount() > 0 && (
                                <Button
                                    type='button'
                                    variant='outline'
                                    size='sm'
                                    className='w-full'
                                    onClick={copyFailedCookies}
                                >
                                    <Copy className='mr-2 h-4 w-4' />
                                    {t('batchModal.copyFailedCookies')}
                                </Button>
                            )}
                        </>
                    )}
                </div>
            )}
        </>
    )

    const footerContent = (
        <>
            {!showResults ? (
                <>
                    <Button type='button' variant='outline' onClick={handleClose}>
                        {t('common.cancel')}
                    </Button>
                    <Button type='submit' disabled={isProcessing || !cookies.trim()}>
                        {isProcessing && <Loader2 className='mr-2 h-4 w-4 animate-spin' />}
                        {t('batchModal.startAdding')}
                    </Button>
                </>
            ) : (
                <Button onClick={handleClose} disabled={isProcessing}>
                    {isProcessing ? t('common.processing') : t('common.done')}
                </Button>
            )}
        </>
    )

    if (isMobile === undefined) {
        return null
    }

    if (!isMobile) {
        return (
            <Dialog open={true} onOpenChange={handleClose}>
                <DialogContent className='sm:max-w-[600px]'>
                    <form onSubmit={handleSubmit}>
                        <DialogHeader>
                            <DialogTitle>{t('batchModal.title')}</DialogTitle>
                            <DialogDescription>{t('batchModal.desc')}</DialogDescription>
                        </DialogHeader>
                        <div className='py-4'>{formContent}</div>
                        <DialogFooter>{footerContent}</DialogFooter>
                    </form>
                </DialogContent>
            </Dialog>
        )
    }

    return (
        <Drawer open={true} onOpenChange={handleClose}>
            <DrawerContent>
                <form onSubmit={handleSubmit} className='max-h-[90vh] overflow-auto'>
                    <DrawerHeader>
                        <DrawerTitle>{t('batchModal.title')}</DrawerTitle>
                        <DrawerDescription>{t('batchModal.desc')}</DrawerDescription>
                    </DrawerHeader>
                    <div className='px-4 pb-4'>{formContent}</div>
                    <DrawerFooter className='flex-row justify-end space-x-2'>{footerContent}</DrawerFooter>
                </form>
            </DrawerContent>
        </Drawer>
    )
}
