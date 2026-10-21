import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/livetrip";

export interface User {
  id: string;
  username: string | null;
  email: string;
  name: string;
  bio: string | null;
  location: string | null;
  avatar: string | null;
  provider: string;
  createdAt: string;
  settings?: { onLeaderboard: boolean; historyPublic: boolean; isBusiness: boolean };
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: () => void;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  setUser: (user: User | null) => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const refresh = async () => {
    try {
      const data = await api<{ user: User }>("/api/auth/me");
      setUser(data.user);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const signIn = async (email: string, password: string) => {
    const data = await api<{ user: User }>("/api/auth/login", { method: "POST", json: { email, password } });
    setUser(data.user);
  };

  const signUp = async (name: string, email: string, password: string) => {
    const data = await api<{ user: User }>("/api/auth/register", { method: "POST", json: { name, email, password } });
    setUser(data.user);
  };

  const login = () => navigate("/login");

  const logout = async () => {
    await api("/api/auth/logout", { method: "POST" });
    setUser(null);
    navigate("/login");
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, signIn, signUp, logout, refresh, setUser, isAuthenticated: !!user }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
