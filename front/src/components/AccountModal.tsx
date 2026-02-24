import { useState, useEffect } from 'react'
import { ChevronDown, ChevronUp, Loader2, AlertCircle } from 'lucide-react'
import type { AccountResponse, AccountCreate, AccountUpdate } from '../api/types'
import { accountsApi } from '../api/client'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Drawer, DrawerContent, DrawerDescription, DrawerFooter, DrawerHeader, DrawerTitle } from '@/components/ui/drawer'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useIsMobile } from '@/hooks/use-mobile'
import { isValidUUID, formatUUID } from '@/utils/validators'

interface AccountModalProps {
    account: AccountResponse | null
    onClose: () => void
}

export function AccountModal({ account, onClose }: AccountModalProps) {
    const [formData, setFormData] = useState({
        cookie_value: '',
        organization_uuid: '',
        capabilities: [] as string[],
    })
    const [accountType, setAccountType] = useState<'none' | 'Free' | 'Pro' | 'Max'>('none')
    const [loading, setLoading] = useState(false)
    const [showAdvanced, setShowAdvanced] = useState(false)
    const [showCookieAlert, setShowCookieAlert] = useState(false)
    const [uuidError, setUuidError] = useState('')
    const isMobile = useIsMobile()

    useEffect(() => {
        if (account) {
            setFormData({
                cookie_value: '',
                organization_uuid: account.organization_uuid,
                capabilities: account.capabilities || [],
            })

            const caps = account.capabilities || []
            if (caps.length === 0) {
                setAccountType('none')
            } else if (caps.includes('claude_max')) {
                setAccountType('Max')
            } else if (caps.includes('claude_pro')) {
                setAccountType('Pro')
            } else {
                setAccountType('Free')
            }
        }
    }, [account])

    const validateAndProcessCookie = (cookieValue: string): { isValid: boolean; processedValue: string } => {
        let processedValue = cookieValue.trim()

        if (processedValue.startsWith('sk-ant-sid01-')) {
            processedValue = `sessionKey=${processedValue}`
        }

        const isValid = processedValue.startsWith('sessionKey=sk-ant-sid01-')

        return { isValid, processedValue }
    }

    const handleSubmitForm = async (e: React.FormEvent) => {
        e.preventDefault()

        if (formData.cookie_value) {
            const { isValid, processedValue } = validateAndProcessCookie(formData.cookie_value)

            formData.cookie_value = processedValue
            setFormData({ ...formData, cookie_value: processedValue })

            if (!isValid) {
                setShowCookieAlert(true)
                return
            }
        }

        await handleSubmitAccount()
    }

    const handleSubmitAccount = async () => {
        setLoading(true)

        let capabilities: string[] | undefined
        switch (accountType) {
            case 'Free':
                capabilities = ['chat']
                break
            case 'Pro':
                capabilities = ['chat', 'claude_pro']
                break
            case 'Max':
                capabilities = ['chat', 'claude_max']
                break
            case 'none':
                capabilities = undefined
                break
        }

        try {
            if (account) {
                // 更新账户
                const updateData: AccountUpdate = {}

                if (formData.cookie_value && formData.cookie_value !== account.cookie_value) {
                    updateData.cookie_value = formData.cookie_value
                }

                if (capabilities) {
                    updateData.capabilities = capabilities
                }

                await accountsApi.update(account.organization_uuid, updateData)
            } else {
                // 创建新账户
                const createData: AccountCreate = {}

                if (formData.cookie_value) {
                    createData.cookie_value = formData.cookie_value
                }

                if (formData.organization_uuid) {
                    createData.organization_uuid = formatUUID(formData.organization_uuid)
                }

                if (capabilities) {
                    createData.capabilities = capabilities
                }

                await accountsApi.create(createData)
            }

            onClose()
        } finally {
            setLoading(false)
        }
    }

    const handleCookieAlertConfirm = async () => {
        setShowCookieAlert(false)
        await handleSubmitAccount()
    }

    const cookieAlertDialog = (
        <AlertDialog open={showCookieAlert} onOpenChange={setShowCookieAlert}>
            <AlertDialogContent>
                <AlertDialogHeader>
                    <AlertDialogTitle>Cookie 格式警告</AlertDialogTitle>
                    <AlertDialogDescription>
                        检测到您输入的 Cookie 格式可能不正确。标准格式应包含 "sessionKey=sk-ant-sid01-" 开头。
                        <br />
                        <br />
                        如果您使用的是反向代理或自定义配置，可以忽略此警告继续提交。
                    </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                    <AlertDialogCancel>取消</AlertDialogCancel>
                    <AlertDialogAction onClick={handleCookieAlertConfirm}>仍然提交</AlertDialogAction>
                </AlertDialogFooter>
            </AlertDialogContent>
        </AlertDialog>
    )

    const formContent = (
        <>
            <div className='grid gap-4 py-4'>
                <div className='space-y-2'>
                    <Label htmlFor='cookie_value'>
                        Cookie <span className='text-destructive'>*</span>
                    </Label>
                    <Textarea
                        id='cookie_value'
                        placeholder='粘贴您的 Claude Cookie...'
                        value={formData.cookie_value}
                        onChange={e => setFormData({ ...formData, cookie_value: e.target.value })}
                        className='min-h-[100px] font-mono text-sm break-all'
                        required
                    />
                </div>

                <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
                    <CollapsibleTrigger asChild>
                        <Button variant='outline' type='button' className='w-full justify-between'>
                            <span>高级选项</span>
                            {showAdvanced ? <ChevronUp className='h-4 w-4' /> : <ChevronDown className='h-4 w-4' />}
                        </Button>
                    </CollapsibleTrigger>
                    <CollapsibleContent className='space-y-4 mt-4'>
                        {!account && (
                            <div className='space-y-2'>
                                <Label htmlFor='organization_uuid'>Organization UUID</Label>
                                <Input
                                    id='organization_uuid'
                                    placeholder='留空自动获取'
                                    value={formData.organization_uuid}
                                    onChange={e => {
                                        const value = e.target.value
                                        setFormData({ ...formData, organization_uuid: value })
                                        const formatted = formatUUID(value)
                                        if (formatted && !isValidUUID(formatted)) {
                                            setUuidError('请输入有效的 UUID 格式')
                                        } else {
                                            setUuidError('')
                                        }
                                    }}
                                    className={uuidError && formData.organization_uuid ? 'border-destructive' : ''}
                                />
                                {uuidError && formData.organization_uuid && (
                                    <div className='flex items-center gap-1 text-sm text-destructive'>
                                        <AlertCircle className='h-3 w-3' />
                                        <span>{uuidError}</span>
                                    </div>
                                )}
                            </div>
                        )}

                        <div className='space-y-2'>
                            <Label htmlFor='accountType'>账户类型</Label>
                            <Select value={accountType} onValueChange={value => setAccountType(value as any)}>
                                <SelectTrigger className='w-full' id='accountType'>
                                    <SelectValue placeholder='选择账户类型' />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value='none'>未选择</SelectItem>
                                    <SelectItem value='Free'>Free</SelectItem>
                                    <SelectItem value='Pro'>Pro</SelectItem>
                                    <SelectItem value='Max'>Max</SelectItem>
                                </SelectContent>
                            </Select>
                        </div>
                    </CollapsibleContent>
                </Collapsible>
            </div>
        </>
    )

    const footerContent = (
        <>
            <Button type='button' variant='outline' onClick={onClose}>
                取消
            </Button>
            <Button
                type='submit'
                disabled={
                    loading ||
                    !formData.cookie_value.trim() ||
                    (!!formData.organization_uuid && !isValidUUID(formatUUID(formData.organization_uuid)))
                }
            >
                {loading && <Loader2 className='mr-2 h-4 w-4 animate-spin' />}
                {loading ? '保存中...' : '保存'}
            </Button>
        </>
    )

    if (isMobile === undefined) {
        return null
    }

    if (!isMobile) {
        return (
            <>
                <Dialog open={true} onOpenChange={onClose}>
                    <DialogContent className='sm:max-w-[600px]'>
                        <form onSubmit={handleSubmitForm}>
                            <DialogHeader>
                                <DialogTitle>{account ? '编辑账户' : '添加 Cookie'}</DialogTitle>
                                <DialogDescription>
                                    {account ? '更新账户的认证信息' : '添加新的 Claude 账户 Cookie'}
                                </DialogDescription>
                            </DialogHeader>
                            {formContent}
                            <DialogFooter>{footerContent}</DialogFooter>
                        </form>
                    </DialogContent>
                </Dialog>
                {cookieAlertDialog}
            </>
        )
    }

    return (
        <>
            <Drawer open={true} onOpenChange={onClose}>
                <DrawerContent>
                    <form onSubmit={handleSubmitForm} className='max-h-[90vh] overflow-auto'>
                        <DrawerHeader>
                            <DrawerTitle>{account ? '编辑账户' : '添加 Cookie'}</DrawerTitle>
                            <DrawerDescription>
                                {account ? '更新账户的认证信息' : '添加新的 Claude 账户 Cookie'}
                            </DrawerDescription>
                        </DrawerHeader>
                        <div className='px-4'>{formContent}</div>
                        <DrawerFooter className='flex-row justify-end space-x-2'>{footerContent}</DrawerFooter>
                    </form>
                </DrawerContent>
            </Drawer>
            {cookieAlertDialog}
        </>
    )
}
