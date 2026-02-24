import { Link, Outlet, useLocation } from 'react-router-dom'
import { Settings, Users, Home, LogOut } from 'lucide-react'
import {
    Sidebar,
    SidebarContent,
    SidebarFooter,
    SidebarGroup,
    SidebarGroupContent,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarProvider,
    SidebarTrigger,
} from '@/components/ui/sidebar'

export function Layout() {
    const location = useLocation()

    const navigation = [
        { name: '仪表板', href: '/', icon: Home },
        { name: '账户管理', href: '/accounts', icon: Users },
        { name: '应用设置', href: '/settings', icon: Settings },
    ]

    const handleLogout = () => {
        localStorage.removeItem('adminKey')
        window.location.href = '/login'
    }

    return (
        <SidebarProvider defaultOpen>
            <div className="flex h-screen w-full">
                <Sidebar variant="sidebar" collapsible="icon">
                    <SidebarHeader>
                        <SidebarMenu>
                            <SidebarMenuItem>
                                <SidebarMenuButton size="lg" className="w-full justify-center md:justify-start">
                                    <div className="flex items-center gap-2">
                                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
                                            <span className="text-lg font-bold text-primary-foreground">C</span>
                                        </div>
                                        <span className="text-xl font-semibold">Clove</span>
                                    </div>
                                </SidebarMenuButton>
                            </SidebarMenuItem>
                        </SidebarMenu>
                    </SidebarHeader>
                    
                    <SidebarContent>
                        <SidebarGroup>
                            <SidebarGroupContent>
                                <SidebarMenu>
                                    {navigation.map((item) => {
                                        const isActive = location.pathname === item.href
                                        return (
                                            <SidebarMenuItem key={item.name}>
                                                <SidebarMenuButton asChild isActive={isActive}>
                                                    <Link to={item.href}>
                                                        <item.icon className="h-4 w-4" />
                                                        <span>{item.name}</span>
                                                    </Link>
                                                </SidebarMenuButton>
                                            </SidebarMenuItem>
                                        )
                                    })}
                                </SidebarMenu>
                            </SidebarGroupContent>
                        </SidebarGroup>
                    </SidebarContent>

                    <SidebarFooter>
                        <SidebarMenu>
                            <SidebarMenuItem>
                                <SidebarMenuButton onClick={handleLogout} className="w-full text-destructive hover:bg-destructive/10 hover:text-destructive">
                                    <LogOut className="h-4 w-4" />
                                    <span>退出登录</span>
                                </SidebarMenuButton>
                            </SidebarMenuItem>
                        </SidebarMenu>
                    </SidebarFooter>
                </Sidebar>

                <div className="flex flex-1 flex-col">
                    <header className="flex h-14 items-center gap-4 border-b px-6 lg:h-16">
                        <SidebarTrigger className="-ml-1" />
                    </header>
                    
                    <main className="flex-1 overflow-y-auto">
                        <div className="container mx-auto max-w-7xl p-6">
                            <Outlet />
                        </div>
                    </main>
                </div>
            </div>
        </SidebarProvider>
    )
}
