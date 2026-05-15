import api from "./api";

export interface User {
  id: string;
  first_name: string;
  last_name?: string | null;
  email: string;
  createdAt?: string;
}

export interface AuthResponse {
  user?: User;
  message: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  first_name: string;
  last_name?: string;
  email: string;
  password: string;
}

export const authService = {
  login: async (data: LoginPayload): Promise<AuthResponse> => {
    const res = await api.post<AuthResponse>("/auth/signIn", data);
    return res.data;
  },

  register: async (data: RegisterPayload): Promise<AuthResponse> => {
    const res = await api.post<AuthResponse>("/auth/signUp", data);
    return res.data;
  },

  logout: async (): Promise<void> => {
    await api.post("/auth/signOut");
  },

  refreshToken: async (): Promise<void> => {
    await api.post("/auth/refresh");
  },

  fetchProfile: async (): Promise<User> => {
    const res = await api.get<{ success: boolean; message: string; data: User }>("/user/me");
    return res.data.data;
  },
};
