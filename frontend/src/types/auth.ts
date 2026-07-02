export interface AuthTokens {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginResponse extends AuthTokens {
  user: {
    id: string;
    github_login: string;
    github_name: string | null;
    github_avatar_url: string | null;
  };
}
