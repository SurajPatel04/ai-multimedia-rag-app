import type { RootState } from "../../app/store";

export const selectUser            = (state: RootState) => state.auth.user;
export const selectIsAuthenticated = (state: RootState) => state.auth.isAuthenticated;
export const selectAuthLoading     = (state: RootState) => state.auth.isLoading;
export const selectAuthError       = (state: RootState) => state.auth.error;