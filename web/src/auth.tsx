import { createContext, FormEvent, useCallback, useContext, useEffect, useState } from "react";
import { Account, api } from "./api";
import { useI18n } from "./i18n";
import wordmark from "./wordmark.svg?raw";

type AuthState = {
  mode: "selfhost" | "hosted";
  user: Account | null;
  refresh: () => Promise<void>;
  signOut: () => Promise<void>;
};
const Ctx = createContext<AuthState>({ mode: "selfhost", user: null, refresh: async () => {}, signOut: async () => {} });

/** Who is reading. Self-hosted glosa has one local reader and no sign-in. */
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<{ mode: AuthState["mode"]; user: Account | null } | null>(null);
  const refresh = useCallback(async () => {
    try {
      setState(await api.me());
    } catch {
      setState({ mode: "selfhost", user: null });
    }
  }, []);
  const signOut = useCallback(async () => {
    await api.logout().catch(() => {});
    setState((s) => (s ? { ...s, user: null } : s));
  }, []);

  useEffect(() => {
    refresh();
    const onSignedOut = () => setState((s) => (s ? { ...s, user: null } : s));
    window.addEventListener("glosa:signed-out", onSignedOut);
    return () => window.removeEventListener("glosa:signed-out", onSignedOut);
  }, [refresh]);

  if (state === null) return null; // a moment, while asking who this is
  if (state.mode === "hosted" && !state.user) {
    return (
      <Ctx.Provider value={{ ...state, refresh, signOut }}>
        <SignInGate />
      </Ctx.Provider>
    );
  }
  return <Ctx.Provider value={{ ...state, refresh, signOut }}>{children}</Ctx.Provider>;
}

function SignInGate() {
  const code = window.location.pathname.match(/^\/join\/([^/]+)/)?.[1];
  return code ? <JoinPage code={decodeURIComponent(code)} /> : <LoginPage />;
}

function AuthCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="auth-page">
      <div className="auth-card">
        <span className="wordmark auth-mark" aria-label="glosa" dangerouslySetInnerHTML={{ __html: wordmark }} />
        <h1>{title}</h1>
        {children}
      </div>
    </div>
  );
}

function LoginPage() {
  const { t } = useI18n();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.login(email, password);
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthCard title={t("auth.signIn")}>
      <form className="auth-form" onSubmit={submit}>
        <label>
          {t("auth.email")}
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          {t("auth.password")}
          <input type="password" autoComplete="current-password" required value={password}
                 onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="error small" role="alert">{error}</p>}
        <button disabled={busy}>{busy ? t("auth.signingIn") : t("auth.signIn")}</button>
      </form>
      <p className="muted small">{t("auth.inviteOnly")}</p>
    </AuthCard>
  );
}

function JoinPage({ code }: { code: string }) {
  const { t } = useI18n();
  const { refresh } = useAuth();
  const [valid, setValid] = useState<boolean | null>(null);
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.checkInvite(code).then((r) => setValid(r.valid)).catch(() => setValid(false));
  }, [code]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.join({ code, ...form });
      window.history.replaceState(null, "", "/");
      await refresh();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (valid === null) return null;
  if (!valid) {
    return (
      <AuthCard title={t("auth.badInvite")}>
        <p className="muted">{t("auth.badInviteHelp")}</p>
        <a className="btn" href="/">{t("auth.signIn")}</a>
      </AuthCard>
    );
  }
  return (
    <AuthCard title={t("auth.join")}>
      <p className="muted small" style={{ margin: 0 }}>{t("auth.joinHelp")}</p>
      <form className="auth-form" onSubmit={submit}>
        <label>
          {t("auth.name")}
          <input autoComplete="name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>
          {t("auth.email")}
          <input type="email" autoComplete="email" required value={form.email}
                 onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </label>
        <label>
          {t("auth.password")}
          <input type="password" autoComplete="new-password" required minLength={10} value={form.password}
                 onChange={(e) => setForm({ ...form, password: e.target.value })} />
          <span className="muted small" style={{ fontWeight: 400 }}>{t("auth.passwordRule")}</span>
        </label>
        {error && <p className="error small" role="alert">{error}</p>}
        <button disabled={busy}>{busy ? t("auth.creating") : t("auth.create")}</button>
      </form>
    </AuthCard>
  );
}
