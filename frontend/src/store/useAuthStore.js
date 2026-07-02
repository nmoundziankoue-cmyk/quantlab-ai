import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi } from "../api/authApi";
import { setAuthToken, clearAuthToken } from "../api/client";

const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      login: async (email, password) => {
        set({ isLoading: true, error: null });
        try {
          // Try enterprise login first (returns refresh token + session)
          let data;
          try {
            data = await authApi.enterpriseLogin({ email, password });
          } catch {
            // Fall back to basic login if enterprise login fails (e.g. DB not running)
            data = await authApi.login({ email, password });
          }
          const token = data.access_token;
          setAuthToken(token);
          set({
            user: data.user,
            token,
            refreshToken: data.refresh_token ?? null,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
          return data;
        } catch (err) {
          set({ isLoading: false, error: err.message });
          throw err;
        }
      },

      register: async (email, password, full_name, role = "ANALYST") => {
        set({ isLoading: true, error: null });
        try {
          const data = await authApi.register({ email, password, full_name, role });
          set({ isLoading: false });
          return data;
        } catch (err) {
          set({ isLoading: false, error: err.message });
          throw err;
        }
      },

      logout: async () => {
        const { token } = get();
        clearAuthToken();
        set({ user: null, token: null, refreshToken: null, isAuthenticated: false, error: null });
        try {
          await authApi.logout(token);
        } catch {
          // Ignore logout errors — client state is already cleared
        }
      },

      refreshAccessToken: async () => {
        const { refreshToken } = get();
        if (!refreshToken) throw new Error("No refresh token");
        try {
          const data = await authApi.refresh(refreshToken);
          setAuthToken(data.access_token);
          set({
            token: data.access_token,
            refreshToken: data.refresh_token ?? refreshToken,
          });
          return data.access_token;
        } catch (err) {
          // Refresh failed — force logout
          get().logout();
          throw err;
        }
      },

      fetchMe: async () => {
        const { token } = get();
        if (!token) return null;
        try {
          const user = await authApi.me(token);
          set({ user, isAuthenticated: true });
          return user;
        } catch {
          return null;
        }
      },

      // Called after zustand rehydrates from localStorage — re-injects the token into axios.
      _hydrateToken: () => {
        const { token } = get();
        if (token) setAuthToken(token);
      },

      clearError: () => set({ error: null }),
    }),
    {
      name: "__quant_auth__",
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.token) setAuthToken(state.token);
      },
    }
  )
);

export default useAuthStore;
