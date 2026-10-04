import { useEffect, useState } from "react";
import { api, Settings, UsageReport } from "../api";
import { useI18n } from "../i18n";

const usd = (n: number) => (n < 0.01 ? `$${n.toFixed(4)}` : `$${n.toFixed(2)}`);

type Props = {
  settings: Settings;
  /** Changes whenever the selected model changes, so the estimates are refreshed. */
  modelKey: string;
  onPrice: (model: string, price: { input: number; output: number } | null) => void;
};

/** What the AI has cost and what each feature costs per call with the selected model. */
export function UsageCard({ settings, modelKey, onPrice }: Props) {
  const { t } = useI18n();
  const [report, setReport] = useState<UsageReport | null>(null);
  const [priceIn, setPriceIn] = useState("");
  const [priceOut, setPriceOut] = useState("");

  useEffect(() => {
    api.usage().then(setReport).catch(() => setReport(null));
  }, [modelKey]);

  if (!report) return null;
  const { model } = report;
  const per100 = (c: number | null) => (c === null ? "—" : usd(c * 100));

  async function savePrice() {
    const input = Number(priceIn.replace(",", "."));
    const output = Number(priceOut.replace(",", "."));
    if (!(input >= 0 && output >= 0)) return;
    onPrice(model.model, { input, output });
    const prices = { ...settings["ai.prices"], [model.model]: { input, output } };
    await api.saveSettings({ "ai.prices": prices });
    setReport(await api.usage());
  }

  return (
    <section className="card">
      <h2>{t("usage.title")}</h2>
      <div className="usage-summary">
        <div>
          <span className="usage-big">{usd(report.total_cost)}</span>
          <span className="muted small">{t("usage.spent", { days: report.days, n: report.calls })}</span>
        </div>
        {report.unpriced_calls > 0 && <p className="warn small">{t("usage.unpriced", { n: report.unpriced_calls })}</p>}
      </div>

      <p className="field-label" style={{ margin: 0 }}>{t("usage.perCall", { model: model.model || "—" })}</p>
      {model.price ? (
        <table className="usage-table">
          <thead>
            <tr>
              <th>{t("usage.feature")}</th>
              <th>{t("usage.oneCall")}</th>
              <th>{t("usage.hundred")}</th>
            </tr>
          </thead>
          <tbody>
            {report.features.map((f) => (
              <tr key={f.feature}>
                <td>
                  {t(`usage.f.${f.feature}` as "usage.f.translate")}
                  {!f.measured && <span className="muted small"> · {t("usage.estimated")}</span>}
                </td>
                <td>{f.cost_per_call === null ? "—" : usd(f.cost_per_call)}</td>
                <td>{per100(f.cost_per_call)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      <p className="muted small" style={{ margin: 0 }}>
        {model.price
          ? model.price.input === 0 && model.price.output === 0
            ? t("usage.free")
            : t("usage.price", { input: model.price.input, output: model.price.output })
          : t("usage.noPrice")}
        {" "}{t("usage.freeParts")}
      </p>
      {(!model.price || model.custom) && model.provider !== "openai_compatible" && (
        <form
          className="price-row"
          onSubmit={(e) => {
            e.preventDefault();
            savePrice();
          }}
        >
          <label>
            {t("usage.inputPrice")}
            <input inputMode="decimal" placeholder={model.price ? String(model.price.input) : "2.50"} value={priceIn} onChange={(e) => setPriceIn(e.target.value)} />
          </label>
          <label>
            {t("usage.outputPrice")}
            <input inputMode="decimal" placeholder={model.price ? String(model.price.output) : "10"} value={priceOut} onChange={(e) => setPriceOut(e.target.value)} />
          </label>
          <button disabled={!priceIn || !priceOut}>{t("usage.savePrice")}</button>
        </form>
      )}
    </section>
  );
}
