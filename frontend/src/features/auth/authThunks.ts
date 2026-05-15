import { createAsyncThunk } from "@reduxjs/toolkit";
import type { AxiosError } from "axios";
import {
  authService,
  type LoginPayload,
  type RegisterPayload,
  type User,
} from "../../services/authService";

const getErrorMessage = (error: unknown, fallback: string) => {
  const axiosError = error as AxiosError<{ message?: string }>;
  return axiosError.response?.data?.message || fallback;
};

export const loginUser = createAsyncThunk<User, LoginPayload>(
  "auth/login",
  async (payload: LoginPayload, { rejectWithValue }) => {
    try {
      await authService.login(payload);
      return await authService.fetchProfile();
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, "Login failed"));
    }
  }
);

export const registerUser = createAsyncThunk<string, RegisterPayload>(
  "auth/register",
  async (payload: RegisterPayload, { rejectWithValue }) => {
    try {
      const res = await authService.register(payload);
      return res.message;
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, "Registration failed"));
    }
  }
);

export const logoutUser = createAsyncThunk(
  "auth/logout",
  async (_, { rejectWithValue }) => {
    try {
      await authService.logout();
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, "Logout failed"));
    }
  }
);

export const fetchProfile = createAsyncThunk<User>(
  "auth/fetchProfile",
  async (_, { rejectWithValue }) => {
    try {
      const data = await authService.fetchProfile();
      return data;
    } catch (error) {
      return rejectWithValue(getErrorMessage(error, "Failed to fetch profile"));
    }
  }
);
