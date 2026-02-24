// 账户相关类型
export interface OAuthToken {
  access_token: string;
  refresh_token: string;
  expires_at: number;
}

export interface AccountCreate {
  cookie_value?: string;
  oauth_token?: OAuthToken;
  organization_uuid?: string;
  capabilities?: string[];
}

export interface AccountUpdate {
  cookie_value?: string;
  oauth_token?: OAuthToken;
  capabilities?: string[];
  status?: 'valid' | 'invalid' | 'rate_limited';
}

export interface OAuthCodeExchange {
  organization_uuid: string;
  code: string;
  pkce_verifier: string;
  capabilities?: string[];
}

export interface AccountResponse {
  organization_uuid: string;
  capabilities?: string[];
  cookie_value?: string; // Masked value
  status: 'valid' | 'invalid' | 'rate_limited';
  auth_type: 'cookie_only' | 'oauth_only' | 'both';
  is_pro: boolean;
  is_max: boolean;
  has_oauth: boolean;
  last_used: string;
  resets_at?: string;
}

// 设置相关类型
export interface SettingsRead {
  api_keys: string[];
  admin_api_keys: string[];
  proxy_url?: string | null;
  claude_ai_url: string;
  claude_api_baseurl: string;
  custom_prompt?: string | null;
  use_real_roles: boolean;
  human_name: string;
  assistant_name: string;
  padtxt_length: number;
  allow_external_images: boolean;
  preserve_chats: boolean;
  oauth_client_id: string;
  oauth_authorize_url: string;
  oauth_token_url: string;
  oauth_redirect_uri: string;
}

export interface SettingsUpdate {
  api_keys?: string[];
  admin_api_keys?: string[];
  proxy_url?: string | null;
  claude_ai_url?: string;
  claude_api_baseurl?: string;
  custom_prompt?: string | null;
  use_real_roles?: boolean;
  human_name?: string;
  assistant_name?: string;
  padtxt_length?: number;
  allow_external_images?: boolean;
  preserve_chats?: boolean;
  oauth_client_id?: string;
  oauth_authorize_url?: string;
  oauth_token_url?: string;
  oauth_redirect_uri?: string;
}

export interface ApiError {
  detail: string;
}

// 统计相关类型
export interface AccountStats {
  total_accounts: number;
  valid_accounts: number;
  rate_limited_accounts: number;
  invalid_accounts: number;
  active_sessions: number;
}

export interface StatisticsResponse {
  status: 'healthy' | 'degraded';
  accounts: AccountStats;
}