import { FormEvent, useEffect, useState } from "react";
import { api, Invite } from "../api";
import { useAuth } from "../auth";
import { useI18n } from "../i18n";

/** The signed-in account on the hosted service: who you are, and a new password. */
export function AccountCard() {
  const { t } = useI18n();
  const { user, signOut } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    try {
      await api.changePassword(current, next);
      setCurrent("");
      setNext("");
      setMessage({ ok: true, text: t("acc.passwordChanged") });
    } catch (err) {
      setMessage({ ok: false, text: (err as Error).message });
    }
  }

  if (!user) return null;
  return (
    <section className="card">
      <h2>{t("acc.title")}</h2>
      <p style={{ margin: 0 }}>
        {user.name ? <><strong>{user.name}</strong> · </> : null}{user.email}
        {user.is_admin && <span className="pill ok" style={{ marginLeft: "0.6rem" }}>{t("acc.admin")}</span>}
      </p>
      <form className="key-row" onSubmit={submit} style={{ flexWrap: "wrap" }}>
        <input type="password" autoComplete="current-password" placeholder={t("acc.current")} value={current}
               onChange={(e) => setCurrent(e.target.value)} required />
        <input type="password" autoComplete="new-password" placeholder={t("acc.new")} value={next} minLength={10}
               onChange={(e) => setNext(e.target.value)} required />
        <button disabled={!current || next.length < 10}>{t("acc.change")}</button>
      </form>
      {message && <p className={message.ok ? "muted small" : "error small"} style={{ margin: 0 }}>{message.text}</p>}
      <div>
        <button className="btn-ghost" onClick={signOut}>{t("auth.signOut")}</button>
      </div>
    </section>
  );
}

/** For the admin: invitation links (each creates one account) and who has joined. */
export function InvitesCard() {
  const { t } = useI18n();
  const [invites, setInvites] = useState<Invite[]>([]);
  const [accounts, setAccounts] = useState<Awaited<ReturnType<typeof api.accounts>>>([]);
  const [note, setNote] = useState("");
  const [copied, setCopied] = useState("");
  const [error, setError] = useState("");

  const load = () => {
    api.invites().then(setInvites).catch((e) => setError(e.message));
    api.accounts().then(setAccounts).catch(() => {});
  };
  useEffect(load, []);

  async function create(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      const invite = await api.createInvite(note);
      setNote("");
      await copy(invite);
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function copy(invite: Invite) {
    try {
      await navigator.clipboard.writeText(invite.url);
      setCopied(invite.code);
    } catch {
      setCopied("");
    }
  }

  const open = invites.filter((i) => !i.used_by);
  return (
    <section className="card">
      <h2>{t("inv.title")}</h2>
      <p className="muted small" style={{ margin: 0 }}>{t("inv.help")}</p>
      <form className="key-row" onSubmit={create}>
        <input placeholder={t("inv.note")} value={note} maxLength={200} onChange={(e) => setNote(e.target.value)} />
        <button>{t("inv.create")}</button>
      </form>
      {error && <p className="error small">{error}</p>}
      {open.length > 0 && (
        <ul className="extras-list">
          {open.map((i) => (
            <li key={i.code} className="extra">
              <div className="extra-text">
                <strong>{i.note || t("inv.noNote")}</strong>
                <code className="invite-url">{i.url}</code>
              </div>
              <div className="extra-actions">
                <button className="btn-ghost" onClick={() => copy(i)}>{copied === i.code ? t("inv.copied") : t("inv.copy")}</button>
                <button className="btn-ghost" onClick={() => api.deleteInvite(i.code).then(load)}>{t("inv.revoke")}</button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <h3 className="small-heading">{t("inv.accounts")}</h3>
      <ul className="extras-list">
        {accounts.map((a) => (
          <li key={a.id} className="extra">
            <div className="extra-text">
              <strong>{a.name || a.email}</strong>
              {a.name && <span className="muted small">{a.email}</span>}
            </div>
            <span className="muted small">{t("inv.counts", { books: String(a.books), terms: String(a.terms) })}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
