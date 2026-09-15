"use client";

import { useEffect, useState, type FormEvent } from "react";
import { CheckCircle2, Loader2, Plug, Send, ShieldAlert } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { deliveryStatusTone } from "@/components/Badge";
import { listDeliveries, submitLead, type DeliveryLog, type LeadValidationResult } from "@/lib/api";
import { mockDeliveries } from "@/lib/mock";
import { formatDate, titleCase } from "@/lib/utils";

const CONNECTED_INTEGRATIONS = [
  { name: "CRM Adapter", detail: "Pluggable target — mock / HubSpot / Salesforce" },
  { name: "Make.com Webhook", detail: "Outbound scenario dispatch for leads & audit-complete events" },
  { name: "Inbound Webhooks", detail: "HMAC-SHA256 signature verification on receipt" },
];

const deliveryColumns: Array<DataTableColumn<DeliveryLog>> = [
  { key: "target", header: "Target", render: (d) => <span className="font-medium text-slate-200">{d.target}</span> },
  { key: "status", header: "Status", render: (d) => <Badge tone={deliveryStatusTone(d.status)}>{titleCase(d.status)}</Badge> },
  { key: "attempts", header: "Attempts", render: (d) => d.attempts },
  {
    key: "error",
    header: "Last Error",
    render: (d) => (d.last_error ? <span className="text-rose-400">{d.last_error}</span> : <span className="text-slate-600">—</span>),
  },
  {
    key: "updated",
    header: "Updated",
    render: (d) => formatDate(d.updated_at, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }),
  },
];

export default function IntegrationsPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [company, setCompany] = useState("");
  const [website, setWebsite] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<LeadValidationResult | null>(null);

  const [deliveries, setDeliveries] = useState<DeliveryLog[]>(mockDeliveries);
  const [deliveriesIsMock, setDeliveriesIsMock] = useState(true);
  const [deliveriesLoading, setDeliveriesLoading] = useState(true);

  async function refreshDeliveries() {
    try {
      const data = await listDeliveries();
      setDeliveries(data);
      setDeliveriesIsMock(false);
    } catch {
      setDeliveries(mockDeliveries);
      setDeliveriesIsMock(true);
    }
  }

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await listDeliveries();
        if (!cancelled) {
          setDeliveries(data);
          setDeliveriesIsMock(false);
        }
      } catch {
        if (!cancelled) {
          setDeliveries(mockDeliveries);
          setDeliveriesIsMock(true);
        }
      } finally {
        if (!cancelled) setDeliveriesLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!email.trim()) return;
    setSubmitting(true);
    setSubmitResult(null);
    try {
      const result = await submitLead({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim(),
        company: company.trim(),
        website: website.trim(),
        message: message.trim(),
        source: "dashboard_widget",
      });
      setSubmitResult(result);
    } catch {
      setSubmitResult({
        valid: true,
        normalized: {
          id: null,
          name: name.trim(),
          email: email.trim(),
          phone: phone.trim() || null,
          company: company.trim() || null,
          website: website.trim() || null,
          source: "dashboard_widget",
          message: message.trim() || null,
          custom_fields: {},
          created_at: null,
        },
        errors: [],
        warnings: ["Running in offline demo mode — this lead was not actually delivered."],
      });
    } finally {
      setSubmitting(false);
      setName("");
      setEmail("");
      setPhone("");
      setCompany("");
      setWebsite("");
      setMessage("");
      await refreshDeliveries();
    }
  }

  return (
    <div>
      <PageHeader title="Integrations" description="Capture leads, push them to your CRM or Make.com, and monitor delivery status." />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-2" title="Capture a Lead" description="e.g. from a mini-audit widget on a marketing site">
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="lead-name" className="label-base">
                  Name
                </label>
                <input id="lead-name" type="text" value={name} onChange={(event) => setName(event.target.value)} className="input-base" />
              </div>
              <div>
                <label htmlFor="lead-email" className="label-base">
                  Email
                </label>
                <input
                  id="lead-email"
                  type="email"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  className="input-base"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label htmlFor="lead-phone" className="label-base">
                  Phone
                </label>
                <input id="lead-phone" type="text" value={phone} onChange={(event) => setPhone(event.target.value)} className="input-base" />
              </div>
              <div>
                <label htmlFor="lead-company" className="label-base">
                  Company
                </label>
                <input
                  id="lead-company"
                  type="text"
                  value={company}
                  onChange={(event) => setCompany(event.target.value)}
                  className="input-base"
                />
              </div>
            </div>
            <div>
              <label htmlFor="lead-website" className="label-base">
                Website
              </label>
              <input
                id="lead-website"
                type="text"
                value={website}
                onChange={(event) => setWebsite(event.target.value)}
                placeholder="https://example.com"
                className="input-base"
              />
            </div>
            <div>
              <label htmlFor="lead-message" className="label-base">
                Message
              </label>
              <textarea
                id="lead-message"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                rows={3}
                className="input-base resize-y"
              />
            </div>
            <button type="submit" disabled={submitting} className="btn-primary w-full">
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Submit Lead
            </button>
          </form>

          {submitResult && (
            <div className="mt-4 space-y-2 rounded-lg border border-surface-border bg-surface-raised p-3 text-xs">
              <p className="flex items-center gap-1.5 font-medium text-emerald-400">
                <CheckCircle2 className="h-3.5 w-3.5" /> Lead {submitResult.valid ? "validated" : "received"}
              </p>
              {submitResult.warnings.map((warning) => (
                <p key={warning} className="flex items-center gap-1.5 text-amber-400">
                  <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {warning}
                </p>
              ))}
              {submitResult.errors.map((error) => (
                <p key={error} className="text-rose-400">
                  {error}
                </p>
              ))}
            </div>
          )}
        </Card>

        <Card className="xl:col-span-3" title="Connected Integrations" description="Configured via environment variables on the backend">
          <ul className="divide-y divide-surface-border">
            {CONNECTED_INTEGRATIONS.map((integration) => (
              <li key={integration.name} className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
                <div className="flex items-center gap-3">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-500/10 text-brand-300">
                    <Plug className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="text-sm font-medium text-slate-200">{integration.name}</p>
                    <p className="text-xs text-slate-500">{integration.detail}</p>
                  </div>
                </div>
                <Badge tone="success" dot>
                  Connected
                </Badge>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card
        className="mt-6"
        title="Delivery Log"
        description={deliveriesIsMock ? "Demo data — API unavailable" : "Live delivery attempts"}
        padded={false}
      >
        {deliveriesLoading ? (
          <div className="flex items-center gap-2 p-8 text-sm text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading delivery log…
          </div>
        ) : (
          <DataTable columns={deliveryColumns} data={deliveries} getRowKey={(d) => d.id} emptyMessage="No deliveries yet." />
        )}
      </Card>
    </div>
  );
}
