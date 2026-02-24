import { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { Key, RefreshCw, Sliders, Globe, Shield, Check, AlertCircle, Loader2, Trash2, Copy, Eye, EyeOff } from 'lucide-react'
import type { SettingsRead, SettingsUpdate } from '../api/types'
import { settingsApi } from '../api/client'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'
import { useIsMobile } from '@/hooks/use-mobile'

export function Settings() {
    const [settings, setSettings] = useState<SettingsRead | null>(null)
    const [originalSettings, setOriginalSettings] = useState<SettingsRead | null>(null)
    const [loading, setLoading] = useState(true)
    const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
    const [newApiKey, setNewApiKey] = useState('')
    const [newAdminKey, setNewAdminKey] = useState('')
    const [visibleKeys, setVisibleKeys] = useState<Set<string>>(new Set())
    const [copiedKeys, setCopiedKeys] = useState<Set<string>>(new Set())
    const isMobile = useIsMobile()
    const { t } = useTranslation()

    const loadSettings = async () => {
        try {
            const response = await settingsApi.get()
            setSettings(response.data)
            setOriginalSettings(response.data)
        } catch (error) {
            console.error('Failed to load settings:', error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadSettings()
    }, [])

    // Immediate save function
    const saveChanges = useCallback(
        async (changes: SettingsUpdate) => {
            if (Object.keys(changes).length === 0) return

            setSaveStatus('saving')
            try {
                await settingsApi.update(changes)
                setSaveStatus('saved')

                // Update original settings to reflect saved changes
                if (originalSettings && settings) {
                    setOriginalSettings({ ...originalSettings, ...changes })
                }

                // Reset status after 3 seconds
                setTimeout(() => setSaveStatus('idle'), 3000)
            } catch (error) {
                console.error('Failed to save settings:', error)
                setSaveStatus('error')
                setTimeout(() => setSaveStatus('idle'), 5000)
            }
        },
        [originalSettings],
    )

    // Update settings without saving
    const updateSettings = useCallback((newSettings: SettingsRead) => {
        setSettings(newSettings)
    }, [])

    // Handle field change and save immediately
    const handleFieldChange = useCallback(
        async (newSettings: SettingsRead) => {
            setSettings(newSettings)

            if (!originalSettings) return

            // Compare and get changed fields
            const changes: SettingsUpdate = {}

            // Check each field for changes
            Object.keys(newSettings).forEach(key => {
                const typedKey = key as keyof SettingsRead
                if (JSON.stringify(newSettings[typedKey]) !== JSON.stringify(originalSettings[typedKey])) {
                    ;(changes as any)[key] = newSettings[typedKey]
                }
            })

            // Save immediately if there are changes
            if (Object.keys(changes).length > 0) {
                await saveChanges(changes)
            }
        },
        [originalSettings, saveChanges],
    )

    const handleAddApiKey = async () => {
        if (!settings || !newApiKey || settings.api_keys.includes(newApiKey)) return
        const newSettings = {
            ...settings,
            api_keys: [...settings.api_keys, newApiKey],
        }
        await handleFieldChange(newSettings)
        setNewApiKey('')
    }

    const handleRemoveApiKey = async (key: string) => {
        if (!settings) return
        const newSettings = {
            ...settings,
            api_keys: settings.api_keys.filter(k => k !== key),
        }
        await handleFieldChange(newSettings)
    }

    const handleAddAdminKey = async () => {
        if (!settings || !newAdminKey || settings.admin_api_keys.includes(newAdminKey)) return
        const newSettings = {
            ...settings,
            admin_api_keys: [...settings.admin_api_keys, newAdminKey],
        }
        await handleFieldChange(newSettings)
        setNewAdminKey('')
    }

    const handleRemoveAdminKey = async (key: string) => {
        if (!settings) return
        const newSettings = {
            ...settings,
            admin_api_keys: settings.admin_api_keys.filter(k => k !== key),
        }
        await handleFieldChange(newSettings)
    }

    const generateNewKey = (type: 'api' | 'admin') => {
        const key =
            'sk-' +
            Array.from({ length: 48 }, () =>
                'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'.charAt(Math.floor(Math.random() * 62)),
            ).join('')

        if (type === 'api') {
            setNewApiKey(key)
        } else {
            setNewAdminKey(key)
        }
    }

    const toggleKeyVisibility = (key: string) => {
        setVisibleKeys(prev => {
            const newSet = new Set(prev)
            if (newSet.has(key)) {
                newSet.delete(key)
            } else {
                newSet.add(key)
            }
            return newSet
        })
    }

    const copyKey = async (key: string) => {
        try {
            await navigator.clipboard.writeText(key)
            toast.success(t('settings.keyCopied'))

            setCopiedKeys(prev => new Set(prev).add(key))
            setTimeout(() => {
                setCopiedKeys(prev => {
                    const newSet = new Set(prev)
                    newSet.delete(key)
                    return newSet
                })
            }, 2000)
        } catch (error) {
            toast.error(t('settings.copyKeyFailed'))
        }
    }

    if (loading || !settings) {
        return (
            <div className='space-y-6'>
                <div className='space-y-2'>
                    <Skeleton className='h-8 w-48' />
                    <Skeleton className='h-4 w-96' />
                </div>

                {[...Array(4)].map((_, i) => (
                    <Card key={i}>
                        <CardHeader>
                            <Skeleton className='h-6 w-32' />
                        </CardHeader>
                        <CardContent className='space-y-4'>
                            <Skeleton className='h-10 w-full' />
                            <Skeleton className='h-10 w-full' />
                        </CardContent>
                    </Card>
                ))}
            </div>
        )
    }

    return (
        <div className='space-y-6'>
            <div className='flex items-center justify-between'>
                <div>
                    <h1 className='text-3xl font-bold tracking-tight pb-1'>{t('settings.title')}</h1>
                    <p className='text-muted-foreground'>{t('settings.subtitle')}</p>
                </div>
                <div className='flex items-center gap-2'>
                    {saveStatus === 'saving' && (
                        <Badge variant='secondary' className='gap-1'>
                            <Loader2 className='h-3 w-3 animate-spin' />
                            {t('common.saving')}
                        </Badge>
                    )}
                    {saveStatus === 'saved' && (
                        <Badge variant='default' className='gap-1 bg-green-500'>
                            <Check className='h-3 w-3' />
                            {t('settings.saved')}
                        </Badge>
                    )}
                    {saveStatus === 'error' && (
                        <Badge variant='destructive' className='gap-1'>
                            <AlertCircle className='h-3 w-3' />
                            {t('settings.saveFailed')}
                        </Badge>
                    )}
                </div>
            </div>

            {/* API Keys */}
            <Card>
                <CardHeader>
                    <CardTitle className='flex items-center gap-2'>
                        <Key className='h-5 w-5' />
                        {t('settings.apiKeys')}
                    </CardTitle>
                    <CardDescription>{t('settings.apiKeysDesc')}</CardDescription>
                </CardHeader>
                <CardContent className='space-y-4'>
                    {settings.api_keys.length === 0 ? (
                        <Alert>
                            <AlertDescription>{t('settings.noApiKeys')}</AlertDescription>
                        </Alert>
                    ) : (
                        <div className='space-y-2'>
                            {settings.api_keys.map((key, index) => (
                                <div
                                    key={index}
                                    className='flex items-start gap-2 p-3 bg-muted/50 rounded-lg border border-border/50 hover:bg-muted/70 transition-colors'
                                >
                                    <code className='flex-1 text-sm font-mono select-none break-all'>
                                        {visibleKeys.has(key) ? key : isMobile ? '*'.repeat(20) : '*'.repeat(32)}
                                    </code>
                                    <div className='flex items-center gap-1 flex-shrink-0'>
                                        <Button
                                            variant='ghost'
                                            size='sm'
                                            onClick={() => toggleKeyVisibility(key)}
                                            className='h-8 w-8 p-0'
                                            title={visibleKeys.has(key) ? t('settings.hideKey') : t('settings.showKey')}
                                        >
                                            {visibleKeys.has(key) ? (
                                                <EyeOff className='h-4 w-4' />
                                            ) : (
                                                <Eye className='h-4 w-4' />
                                            )}
                                        </Button>
                                        <Button
                                            variant='ghost'
                                            size='sm'
                                            onClick={() => copyKey(key)}
                                            className='h-8 w-8 p-0'
                                            title={t('settings.copyKey')}
                                        >
                                            {copiedKeys.has(key) ? (
                                                <Check className='h-4 w-4 text-green-500' />
                                            ) : (
                                                <Copy className='h-4 w-4' />
                                            )}
                                        </Button>
                                        <AlertDialog>
                                            <AlertDialogTrigger asChild>
                                                <Button
                                                    variant='ghost'
                                                    size='sm'
                                                    className='h-8 w-8 p-0 text-destructive hover:text-destructive'
                                                >
                                                    <Trash2 className='h-4 w-4' />
                                                </Button>
                                            </AlertDialogTrigger>
                                            <AlertDialogContent>
                                                <AlertDialogHeader>
                                                    <AlertDialogTitle>{t('settings.deleteKeyTitle')}</AlertDialogTitle>
                                                    <AlertDialogDescription>
                                                        {t('settings.deleteApiKeyDesc')}
                                                    </AlertDialogDescription>
                                                </AlertDialogHeader>
                                                <AlertDialogFooter>
                                                    <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
                                                    <AlertDialogAction onClick={() => handleRemoveApiKey(key)}>
                                                        {t('common.delete')}
                                                    </AlertDialogAction>
                                                </AlertDialogFooter>
                                            </AlertDialogContent>
                                        </AlertDialog>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    <Separator />

                    <div className='space-y-2'>
                        <Label htmlFor='new-api-key'>{t('settings.addNewApiKey')}</Label>
                        <div className='flex flex-wrap gap-2'>
                            <Input
                                id='new-api-key'
                                value={newApiKey}
                                onChange={e => setNewApiKey(e.target.value)}
                                placeholder={t('settings.enterOrGenerateKey')}
                                className='font-mono flex-1 min-w-0'
                            />
                            <div className='flex gap-2'>
                                <Button variant='outline' size='icon' onClick={() => generateNewKey('api')} title={t('settings.generateKey')}>
                                    <RefreshCw className='h-4 w-4' />
                                </Button>
                                <Button onClick={handleAddApiKey} disabled={!newApiKey}>
                                    {t('common.add')}
                                </Button>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Admin Keys */}
            <Card>
                <CardHeader>
                    <CardTitle className='flex items-center gap-2'>
                        <Shield className='h-5 w-5' />
                        {t('settings.adminKeys')}
                    </CardTitle>
                    <CardDescription>{t('settings.adminKeysDesc')}</CardDescription>
                </CardHeader>
                <CardContent className='space-y-4'>
                    {settings.admin_api_keys.length === 0 ? (
                        <Alert>
                            <AlertDescription>{t('settings.noAdminKeys')}</AlertDescription>
                        </Alert>
                    ) : (
                        <div className='space-y-2'>
                            {settings.admin_api_keys.map((key, index) => (
                                <div
                                    key={index}
                                    className='flex items-start gap-2 p-3 bg-muted/50 rounded-lg border border-border/50 hover:bg-muted/70 transition-colors'
                                >
                                    <code className='flex-1 text-sm font-mono select-none break-all'>
                                        {visibleKeys.has(key) ? key : isMobile ? '*'.repeat(20) : '*'.repeat(32)}
                                    </code>
                                    <div className='flex items-center gap-1 flex-shrink-0'>
                                        <Button
                                            variant='ghost'
                                            size='sm'
                                            onClick={() => toggleKeyVisibility(key)}
                                            className='h-8 w-8 p-0'
                                            title={visibleKeys.has(key) ? t('settings.hideKey') : t('settings.showKey')}
                                        >
                                            {visibleKeys.has(key) ? (
                                                <EyeOff className='h-4 w-4' />
                                            ) : (
                                                <Eye className='h-4 w-4' />
                                            )}
                                        </Button>
                                        <Button
                                            variant='ghost'
                                            size='sm'
                                            onClick={() => copyKey(key)}
                                            className='h-8 w-8 p-0'
                                            title={t('settings.copyKey')}
                                        >
                                            {copiedKeys.has(key) ? (
                                                <Check className='h-4 w-4 text-green-500' />
                                            ) : (
                                                <Copy className='h-4 w-4' />
                                            )}
                                        </Button>
                                        <AlertDialog>
                                            <AlertDialogTrigger asChild>
                                                <Button
                                                    variant='ghost'
                                                    size='sm'
                                                    className='h-8 w-8 p-0 text-destructive hover:text-destructive'
                                                >
                                                    <Trash2 className='h-4 w-4' />
                                                </Button>
                                            </AlertDialogTrigger>
                                            <AlertDialogContent>
                                                <AlertDialogHeader>
                                                    <AlertDialogTitle>{t('settings.deleteKeyTitle')}</AlertDialogTitle>
                                                    <AlertDialogDescription>
                                                        {t('settings.deleteAdminKeyDesc')}
                                                    </AlertDialogDescription>
                                                </AlertDialogHeader>
                                                <AlertDialogFooter>
                                                    <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
                                                    <AlertDialogAction onClick={() => handleRemoveAdminKey(key)}>
                                                        {t('common.delete')}
                                                    </AlertDialogAction>
                                                </AlertDialogFooter>
                                            </AlertDialogContent>
                                        </AlertDialog>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    <Separator />

                    <div className='space-y-2'>
                        <Label htmlFor='new-admin-key'>{t('settings.addNewAdminKey')}</Label>
                        <div className='flex flex-wrap gap-2'>
                            <Input
                                id='new-admin-key'
                                value={newAdminKey}
                                onChange={e => setNewAdminKey(e.target.value)}
                                placeholder={t('settings.enterOrGenerateKey')}
                                className='font-mono flex-1 min-w-0'
                            />
                            <div className='flex gap-2'>
                                <Button
                                    variant='outline'
                                    size='icon'
                                    onClick={() => generateNewKey('admin')}
                                    title={t('settings.generateKey')}
                                >
                                    <RefreshCw className='h-4 w-4' />
                                </Button>
                                <Button onClick={handleAddAdminKey} disabled={!newAdminKey}>
                                    {t('common.add')}
                                </Button>
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Claude Settings */}
            <Card>
                <CardHeader>
                    <CardTitle className='flex items-center gap-2'>
                        <Globe className='h-5 w-5' />
                        {t('settings.claudeConfig')}
                    </CardTitle>
                    <CardDescription>{t('settings.claudeConfigDesc')}</CardDescription>
                </CardHeader>
                <CardContent className='space-y-4'>
                    <div className='grid gap-4 md:grid-cols-2'>
                        <div className='space-y-2'>
                            <Label htmlFor='claude-ai-url'>Claude AI URL</Label>
                            <Input
                                id='claude-ai-url'
                                value={settings.claude_ai_url}
                                onChange={e => updateSettings({ ...settings, claude_ai_url: e.target.value })}
                                onBlur={() => handleFieldChange(settings)}
                            />
                        </div>

                        <div className='space-y-2'>
                            <Label htmlFor='claude-api-baseurl'>Claude API Base URL</Label>
                            <Input
                                id='claude-api-baseurl'
                                value={settings.claude_api_baseurl}
                                onChange={e => updateSettings({ ...settings, claude_api_baseurl: e.target.value })}
                                onBlur={() => handleFieldChange(settings)}
                            />
                        </div>

                        <div className='space-y-2 md:col-span-2'>
                            <Label htmlFor='proxy-url'>{t('settings.proxyUrl')}</Label>
                            <Input
                                id='proxy-url'
                                value={settings.proxy_url || ''}
                                onChange={e => updateSettings({ ...settings, proxy_url: e.target.value || null })}
                                onBlur={() => handleFieldChange(settings)}
                                placeholder={t('settings.proxyUrlPlaceholder')}
                            />
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Chat Settings */}
            <Card>
                <CardHeader>
                    <CardTitle className='flex items-center gap-2'>
                        <Sliders className='h-5 w-5' />
                        {t('settings.formatSettings')}
                    </CardTitle>
                    <CardDescription>{t('settings.formatSettingsDesc')}</CardDescription>
                </CardHeader>
                <CardContent className='space-y-6'>
                    <div className='space-y-2'>
                        <Label htmlFor='custom-prompt'>{t('settings.customPrompt')}</Label>
                        <Textarea
                            id='custom-prompt'
                            value={settings.custom_prompt || ''}
                            onChange={e => updateSettings({ ...settings, custom_prompt: e.target.value || null })}
                            onBlur={() => handleFieldChange(settings)}
                            placeholder={t('settings.customPromptPlaceholder')}
                            className='min-h-[100px]'
                        />
                    </div>

                    <Separator />

                    <div className='grid gap-4 md:grid-cols-3'>
                        <div className='space-y-2'>
                            <Label htmlFor='human-name'>{t('settings.humanName')}</Label>
                            <Input
                                id='human-name'
                                value={settings.human_name}
                                onChange={e => updateSettings({ ...settings, human_name: e.target.value })}
                                onBlur={() => handleFieldChange(settings)}
                            />
                        </div>

                        <div className='space-y-2'>
                            <Label htmlFor='assistant-name'>{t('settings.assistantName')}</Label>
                            <Input
                                id='assistant-name'
                                value={settings.assistant_name}
                                onChange={e => updateSettings({ ...settings, assistant_name: e.target.value })}
                                onBlur={() => handleFieldChange(settings)}
                            />
                        </div>

                        <div className='space-y-2'>
                            <Label htmlFor='padtxt-length'>{t('settings.paddingLength')}</Label>
                            <Input
                                id='padtxt-length'
                                type='number'
                                value={settings.padtxt_length}
                                onChange={e => updateSettings({ ...settings, padtxt_length: parseInt(e.target.value) || 0 })}
                                onBlur={() => handleFieldChange(settings)}
                            />
                        </div>
                    </div>

                    <Separator />

                    <div className='space-y-4'>
                        <div className='flex items-center justify-between'>
                            <div className='space-y-0.5'>
                                <Label htmlFor='use-real-roles'>{t('settings.useRealRoles')}</Label>
                                <p className='text-sm text-muted-foreground'>{t('settings.useRealRolesDesc')}</p>
                            </div>
                            <Switch
                                id='use-real-roles'
                                checked={settings.use_real_roles}
                                onCheckedChange={checked => handleFieldChange({ ...settings, use_real_roles: checked })}
                            />
                        </div>

                        <div className='flex items-center justify-between'>
                            <div className='space-y-0.5'>
                                <Label htmlFor='allow-external-images'>{t('settings.allowExternalImages')}</Label>
                                <p className='text-sm text-muted-foreground'>{t('settings.allowExternalImagesDesc')}</p>
                            </div>
                            <Switch
                                id='allow-external-images'
                                checked={settings.allow_external_images}
                                onCheckedChange={checked => handleFieldChange({ ...settings, allow_external_images: checked })}
                            />
                        </div>

                        <div className='flex items-center justify-between'>
                            <div className='space-y-0.5'>
                                <Label htmlFor='preserve-chats'>{t('settings.preserveChats')}</Label>
                                <p className='text-sm text-muted-foreground'>{t('settings.preserveChatsDesc')}</p>
                            </div>
                            <Switch
                                id='preserve-chats'
                                checked={settings.preserve_chats}
                                onCheckedChange={checked => handleFieldChange({ ...settings, preserve_chats: checked })}
                            />
                        </div>
                    </div>
                </CardContent>
            </Card>
        </div>
    )
}
