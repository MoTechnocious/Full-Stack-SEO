"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Check, Copy, KeyRound, Loader2, Lock, ShieldAlert, Trash2 } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { type BadgeTone } from "@/components/Badge";
import { useAuth } from "@/lib/auth";
import { ApiError, createApiKey, listApiKeys, revokeApiKey, type ApiKey, type CreateApiKeyResult } from "@/lib/api";
import { mockApiKeys } from "@/lib/mock";
import { formatDate, titleCase } from "@/lib/utils";

const ROLE_OPTIONS = ["agency_admin", "editor", "client"] as const;

function roleTone(role: string): BadgeTone {
  switch (role) {
    case "owner":
      return "brand";
    case "agency_admin":
      return "info";
    case "editor":
      return "success";
    default:
      return "neutral";
  }
}

export default function ApiKeysPage() {
  const { canManageTeam } = useAuth();

  const [keys, setKeys] = useState<ApiKey[]>(mockApiKeys);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [role, setRole] = useState<(typeof ROLE_OPTIONS)[number]>("editor");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [created, setCreated] = useState<CreateApiKeyResult | null>(null);
  const [copied, setCopied] = useState(false);

  function refresh() {
    setLoading(true);
    listApiKeys()
      .then((result) => {
        setKeys(result);
        setNotice(null);
      })
      .catch((err) => {
        setKeys(mockApiKeys);
        setNotice(
          err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.",
        );
      })
      .finally(() => setLoading(false));
  }

  useEffect(refresh, []);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    setCreateError(null);
    setCreated(null);
    try {
      const result = await createApiKey({ name: name.trim() || "default", role });
      setCreated(result);
      setName("");
      refresh();
    } catch (err) {
      setCreateError(err instanceof ApiError ? err.message : "Could not reach the API — key was not created.");
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(id: string) {
    setRevokingId(id);
    try {
      await revokeApiKey(id);
      setKeys((current) => current.map((key) => (key.id === id ? { ...key, revoked: true } : key)));
    } catch {
      // Leave the row as-is; the notice banner (if any) already explains offline state.
    } finally {
      setRevokingId(null);
    }
  }

  function copySecret(secret: string) {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(secret).catch(() => undefined);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const columns: Array<DataTableColumn<ApiKey>> = [
    { key: "name", header: "Name", render: (key) => <span className="font-medium text-slate-200">{key.name}</span> },
    {
      key: "key",
      header: "Key",
      render: (key) => <code className="text-xs text-slate-400">{key.prefix}••••••••{key.last4}</code>,
    },
    { key: "role", header: "Role", render: (key) => <Badge tone={roleTone(key.role)}>{titleCase(key.role)}</Badge> },
    {
      key: "status",
      header: "Status",
      render: (key) => <Badge tone={key.revoked ? "danger" : "success"}>{key.revoked ? "Revoked" : "Active"}</Badge>,
    },
    { key: "created", header: "Created", render: (key) => <span className="text-xs text-slate-500">{formatDate(key.created_at)}</span> },
    {
      key: "last_used",
      header: "Last used",
      render: (key) => <span className="text-xs text-slate-500">{key.last_used_at ? formatDate(key.last_used_at) : "Never"}</span>,
    },
    {
      key: "actions",
      header: "",
      render: (key) =>
        canManageTeam && !key.revoked ? (
          <button
            type="button"
            onClick={() => handleRevoke(key.id)}
            disabled={revokingId === key.id}
            className="inline-flex items-center gap-1.5 rounded-lg border border-surface-border px-2.5 py-1.5 text-xs font-medium text-rose-300 transition hover:border-rose-500/40 hover:bg-rose-500/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {revokingId === key.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
            Revoke
          </button>
        ) : null,
    },
  ];

  return (
    <div>
      <PageHeader title="API Keys" description="Create keys for programmatic access to the SEO API and MCP server." />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-3" title="Keys" description={`${keys.length} key${keys.length === 1 ? "" : "s"}`} padded={false}>
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading keys…
            </div>
          ) : (
            <DataTable columns={columns} data={keys} getRowKey={(key) => key.id} emptyMessage="No API keys yet." />
          )}
          {notice && (
            <p className="flex items-center gap-1.5 border-t border-surface-border px-4 py-3 text-xs text-amber-400">
              <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
            </p>
          )}
        </Card>

        <Card className="xl:col-span-2" title="Create a key" description="Owners and agency admins can manage keys.">
          {!canManageTeam ? (
            <p className="flex items-start gap-2 text-sm text-slate-500">
              <Lock className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" />
              Your role doesn&apos;t include API key management. Ask an owner or agency admin for a key.
            </p>
          ) : (
            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label htmlFor="key-name" className="label-base">
                  Name
                </label>
                <input
                  id="key-name"
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="CI pipeline"
                  className="input-base"
                />
              </div>
              <div>
                <label htmlFor="key-role" className="label-base">
                  Role
                </label>
                <select id="key-role" value={role} onChange={(event) => setRole(event.target.value as (typeof ROLE_OPTIONS)[number])} className="input-base">
                  {ROLE_OPTIONS.map((option) => (
                    <option key={option} value={option}>
                      {titleCase(option)}
                    </option>
                  ))}
                </select>
              </div>

              <button type="submit" disabled={creating} className="btn-primary w-full">
                {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <KeyRound className="h-4 w-4" />}
                Create key
              </button>

              {createError && (
                <p className="flex items-start gap-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
                  <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {createError}
                </p>
              )}

              {created && (
                <div className="space-y-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                  <p className="text-xs font-medium text-emerald-300">{created.note}</p>
                  <div className="flex items-center gap-2">
                    <code className="min-w-0 flex-1 truncate rounded-md bg-surface-raised px-2 py-1.5 text-[11px] text-slate-300">
                      {created.secret}
                    </code>
                    <button
                      type="button"
                      onClick={() => copySecret(created.secret)}
                      className="btn-secondary shrink-0 !px-2.5 !py-1.5"
                      title="Copy secret"
                    >
                      {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                </div>
              )}
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}
