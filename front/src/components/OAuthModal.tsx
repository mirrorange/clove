import { useState } from 'react'
import { ExternalLink, Info, Loader2, AlertCircle } from 'lucide-react'
import { accountsApi } from '../api/client'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from '@/components/ui/drawer'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useIsMobile } from '@/hooks/use-mobile'
import { isValidUUID, formatUUID } from '@/utils/validators'
import { cn } from '@/lib/utils'

interface OAuthModalProps {
    onClose: () => void
}

// Claude OAuth constants
const CLIENT_ID = '9d1c250a-e61b-44d9-88ed-5944d1962f5e'
const AUTHORIZE_URL = 'https://claude.ai/oauth/authorize'
const REDIRECT_URI = 'https://console.anthropic.com/oauth/code/callback'

export function OAuthModal({ onClose }: OAuthModalProps) {
    const [organizationUuid, setOrganizationUuid] = useState('')
    const [accountType, setAccountType] = useState<'Pro' | 'Max'>('Pro')
    const [authCode, setAuthCode] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')
    const [uuidError, setUuidError] = useState('')
    const [step, setStep] = useState<'input' | 'code'>('input')
    const [pkceVerifier, setPkceVerifier] = useState('')
    const isMobile = useIsMobile()

    // PKCE generation functions
    const generatePKCE = () => {
        // Generate random verifier
        const array = new Uint8Array(32)
        crypto.getRandomValues(array)
        const verifier = btoa(String.fromCharCode.apply(null, Array.from(array)))
            .replace(/\+/g, '-')
            .replace(/\//g, '_')
            .replace(/=/g, '')

        // Generate challenge
        const encoder = new TextEncoder()
        const data = encoder.encode(verifier)
        return crypto.subtle.digest('SHA-256', data).then(buffer => {
            const challenge = btoa(String.fromCharCode.apply(null, Array.from(new Uint8Array(buffer))))
                .replace(/\+/g, '-')
                .replace(/\//g, '_')
                .replace(/=/g, '')
            return { verifier, challenge }
        })
    }

    const handleGenerateUrl = async () => {
        if (!organizationUuid.trim()) {
            setError('请输入 Organization UUID')
            return
        }

        setLoading(true)
        setError('')

        try {
            const { verifier, challenge } = await generatePKCE()
            setPkceVerifier(verifier)

            // Build authorization URL
            const params = new URLSearchParams({
                response_type: 'code',
                client_id: CLIENT_ID,
                organization_uuid: formatUUID(organizationUuid),
                redirect_uri: REDIRECT_URI,
                scope: 'user:profile user:inference',
                state: verifier,
                code_challenge: challenge,
                code_challenge_method: 'S256',
            })

            const authUrl = `${AUTHORIZE_URL}?${params.toString()}`

            // Open in new window
            window.open(authUrl, '_blank', 'width=600,height=700')

            setStep('code')
        } catch (err) {
            setError('生成授权 URL 失败')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const handleExchangeToken = async () => {
        if (!authCode.trim()) {
            setError('请输入授权码')
            return
        }

        setLoading(true)
        setError('')

        try {
            // 发送 code 到后端进行 token 交换
            const exchangeData = {
                organization_uuid: formatUUID(organizationUuid),
                code: authCode,
                pkce_verifier: pkceVerifier,
                capabilities:
                    accountType === 'Max' ? ['chat', 'claude_max'] : accountType === 'Pro' ? ['chat', 'claude_pro'] : ['chat'],
            }

            await accountsApi.exchangeOAuthCode(exchangeData)
            onClose()
        } catch (err) {
            console.error('OAuth exchange error:', err)
            setError('授权失败，请重试')
        } finally {
            setLoading(false)
        }
    }

    const formContent = (
        <>
            <Alert className={cn(isMobile && 'mb-4')}>
                <Info className='h-4 w-4' />
                <AlertDescription>
                    推荐使用 Cookie 添加账户，Clove 可以自动完成认证。OAuth 登录仅作为备选方案。
                </AlertDescription>
            </Alert>

            {step === 'input' ? (
                <div className='grid gap-4'>
                    <div className='space-y-2'>
                        <Label htmlFor='organization_uuid'>
                            Organization UUID <span className='text-destructive'>*</span>
                        </Label>
                        <Input
                            id='organization_uuid'
                            placeholder='请输入您的 Organization UUID'
                            value={organizationUuid}
                            onChange={e => {
                                const value = e.target.value
                                setOrganizationUuid(value)
                                // 验证 UUID 格式
                                const formatted = formatUUID(value)
                                if (formatted && !isValidUUID(formatted)) {
                                    setUuidError('请输入有效的 UUID 格式')
                                } else {
                                    setUuidError('')
                                }
                            }}
                            className={`font-mono ${uuidError && organizationUuid ? 'border-destructive' : ''}`}
                        />
                        {uuidError && organizationUuid ? (
                            <div className='flex items-center gap-1 text-sm text-destructive'>
                                <AlertCircle className='h-3 w-3' />
                                <span>{uuidError}</span>
                            </div>
                        ) : (
                            <p className='text-sm text-muted-foreground'>可在 Claude.ai Cookie 中的 lastActiveOrg 字段找到</p>
                        )}
                    </div>

                    <div className='space-y-2'>
                        <Label htmlFor='accountType'>账户类型</Label>
                        <Select value={accountType} onValueChange={value => setAccountType(value as any)}>
                            <SelectTrigger className='w-full' id='accountType'>
                                <SelectValue placeholder='选择账户类型' />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value='Pro'>Pro</SelectItem>
                                <SelectItem value='Max'>Max</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    {error && (
                        <Alert variant='destructive'>
                            <AlertCircle className='h-4 w-4' />
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}
                </div>
            ) : (
                <div className='grid gap-4'>
                    <Alert>
                        <Info className='h-4 w-4' />
                        <AlertDescription>
                            已在新窗口打开授权页面。完成授权后，请复制授权码并粘贴到下方输入框。
                        </AlertDescription>
                    </Alert>

                    <div className='space-y-2'>
                        <Label htmlFor='auth_code'>
                            授权码 <span className='text-destructive'>*</span>
                        </Label>
                        <Input
                            id='auth_code'
                            placeholder='请粘贴授权码'
                            value={authCode}
                            onChange={e => setAuthCode(e.target.value)}
                            className='font-mono'
                        />
                    </div>

                    {error && (
                        <Alert variant='destructive'>
                            <AlertCircle className='h-4 w-4' />
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}
                </div>
            )}
        </>
    )

    const footerContent = (
        <>
            <Button type='button' variant='outline' onClick={onClose}>
                取消
            </Button>
            {step === 'input' ? (
                <Button
                    onClick={handleGenerateUrl}
                    disabled={loading || !organizationUuid.trim() || !isValidUUID(formatUUID(organizationUuid))}
                >
                    {loading && <Loader2 className='mr-2 h-4 w-4 animate-spin' />}
                    {loading ? (
                        '生成中...'
                    ) : (
                        <>
                            <ExternalLink className='mr-2 h-4 w-4' />
                            开始授权
                        </>
                    )}
                </Button>
            ) : (
                <Button onClick={handleExchangeToken} disabled={loading || !authCode.trim()}>
                    {loading && <Loader2 className='mr-2 h-4 w-4 animate-spin' />}
                    {loading ? '验证中...' : '完成授权'}
                </Button>
            )}
        </>
    )

    if (isMobile === undefined) {
        return null
    }

    if (!isMobile) {
        return (
            <Dialog open={true} onOpenChange={onClose}>
                <DialogContent className='sm:max-w-[600px]'>
                    <DialogHeader>
                        <DialogTitle>OAuth 登录</DialogTitle>
                        <DialogDescription>使用 OAuth 方式添加 Claude 账户</DialogDescription>
                    </DialogHeader>
                    {formContent}
                    <DialogFooter>{footerContent}</DialogFooter>
                </DialogContent>
            </Dialog>
        )
    }

    return (
        <Drawer open={true} onOpenChange={onClose}>
            <DrawerContent>
                <div className='max-h-[90vh] overflow-auto'>
                    <DrawerHeader>
                        <DrawerTitle>OAuth 登录</DrawerTitle>
                        <DrawerDescription>使用 OAuth 方式添加 Claude 账户</DrawerDescription>
                    </DrawerHeader>
                    <div className='px-4'>{formContent}</div>
                    <DrawerFooter className='flex-row justify-end space-x-2'>{footerContent}</DrawerFooter>
                </div>
            </DrawerContent>
        </Drawer>
    )
}
