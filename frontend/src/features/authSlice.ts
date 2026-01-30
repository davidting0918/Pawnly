import { createSlice, type PayloadAction } from '@reduxjs/toolkit';

interface User {
  id: number;
  username: string;
  token: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
}

const initialState: AuthState = {
  user: null,
  isAuthenticated: false,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginSuccess: (state, action: PayloadAction<User>) => {
      state.user = action.payload;
      state.isAuthenticated = true;
      // No need to set localStorage here, redux-persist handles it
    },
    logout: (state) => {
      state.user = null;
      state.isAuthenticated = false;
      // redux-persist will clear storage on logout if configured
    },
  },
});

export const { loginSuccess, logout } = authSlice.actions;
export default authSlice.reducer;
