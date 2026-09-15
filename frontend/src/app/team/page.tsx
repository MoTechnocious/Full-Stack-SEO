"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Check, Copy, Loader2, Lock, ShieldAlert, UserPlus } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { type BadgeTone } from "@/components/Badge";
import { useAuth } from "@/lib/auth";
import { ApiError, createInvite, listMembers, type Invite, type Member } from "@/lib/api";
import { mockMembers } from "@/lib/mock";
import { formatDate, titleCase } from "@/lib/utils";

const ROLE_OPTIONS = ["owner", "agency_admin", "editor", "client"] as const;

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

function statusTone(status: string): BadgeTone {
  switch (status) {
    case "active":
      return "success";
    case "invited":
      return "info";
    case "suspended":
      return "danger";
    default:
      return "neutral";
  }
}

export default function TeamPage() {
  const { canManageTeam } = useAuth();

  const [members, setMembers] = useState<Member[]>(mockMembers);
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState<string | null>(null);

  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<(typeof ROLE_OPTIONS)[number]>("editor");
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);
  const [lastInvite, setLastInvite] = useState<Invite | null>(null);
  const [copied, setCopied] = useState<"token" | "link" | null>(null);

  useEffect(() => {
    let cancelled = false;
    listMembers()
      .then((result) => {
        if (!cancelled) {
          setMembers(result);
          setNotice(null);
        }
      })
      .catch((err) => {
        if (cancelled) return;
        setMembers(mockMembers);
        setNotice(err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleInvite(event: FormEvent) {
    event.preventDefault();
    if (!inviteEmail.trim()) return;
    setInviting(true);
    setInviteError(null);
    setLastInvite(null);
    try {
      const invite = await createInvite({ email: inviteEmail.trim(), role: inviteRole });
      setLastInvite(invite);
      setInviteEmail("");
    } catch (err) {
      setInviteError(err instanceof ApiError ? err.message : "Could not reach the API — invite was not sent.");
    } finally {
      setInviting(false);
    }
  }

  function copy(value: string, kind: "token" | "link") {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(value).catch(() => undefined);
    }
    setCopied(kind);
    setTimeout(() => setCopied((current) => (current === kind ? null : current)), 1500);
  }

  const inviteLink =
    lastInvite && typeof window !== "undefined"
      ? `${window.location.origin}/accept-invite?token=${encodeURIComponent(lastInvite.token)}`
      : null;

  const columns: Array<DataTableColumn<Member>> = [
    { key: "email", header: "Email", render: (member) => <span className="text-slate-200">{member.email ?? "—"}</span> },
    { key: "role", header: "Role", render: (member) => <Badge tone={roleTone(member.role)}>{titleCase(member.role)}</Badge> },
    { key: "status", header: "Status", render: (member) => <Badge tone={statusTone(member.status)}>{titleCase(member.status)}</Badge> },
  ];

  return (
    <div>
      <PageHeader title="Team" description="Members of your organization, and pending invites." />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-3" title="Members" description={`${members.length} member${members.length === 1 ? "" : "s"}`} padded={false}>
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading members…
            </div>
          ) : (
            <DataTable columns={columns} data={members} getRowKey={(member) => member.user_id} emptyMessage="No members yet." />
          )}
          {notice && (
            <p className="flex items-center gap-1.5 border-t border-surface-border px-4 py-3 text-xs text-amber-400">
              <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
            </p>
          )}
        </Card>

        <Card className="xl:col-span-2" title="Invite a teammate" description="Owners and agency admins can invite.">
          {!canManageTeam ? (
            <p className="flex items-start gap-2 text-sm text-slate-500">
              <Lock className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" />
              Your role doesn&apos;t include team management. Ask an owner or agency admin to invite new members.
            </p>
          ) : (
            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label htmlFor="invite-email" className="label-base">
                  Email
                </label>
                <input
                  id="invite-email"
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(event) => setInviteEmail(event.target.value)}
                  placeholder="teammate@company.com"
                  className="input-base"
                />
              </div>
              <div>
                <label htmlFor="invite-role" className="label-base">
                  Role
                </label>
                <select
                  id="invite-role"
                  value={inviteRole}
                  onChange={(event) => setInviteRole(event.target.value as (typeof ROLE_OPTIONS)[number])}
                  className="input-base"
                >
                  {ROLE_OPTIONS.map((role) => (
                    <option key={role} value={role}>
                      {titleCase(role)}
                    </option>
                  ))}
                </select>
              </div>

              <button type="submit" disabled={inviting} className="btn-primary w-full">
                {inviting ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
                Send invite
              </button>

              {inviteError && (
                <p className="flex items-start gap-1.5 rounded-lg border border-rose-500/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
                  <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" /> {inviteError}
                </p>
              )}

              {lastInvite && (
                <div className="space-y-2 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                  <p className="text-xs font-medium text-emerald-300">
                    Invite created for {lastInvite.email} ({titleCase(lastInvite.role)})
                    {lastInvite.expires_at ? ` — expires ${formatDate(lastInvite.expires_at)}` : ""}.
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="min-w-0 flex-1 truncate rounded-md bg-surface-raised px-2 py-1.5 text-[11px] text-slate-300">
                      {lastInvite.token}
                    </code>
                    <button
                      type="button"
                      onClick={() => copy(lastInvite.token, "token")}
                      className="btn-secondary shrink-0 !px-2.5 !py-1.5"
                      title="Copy invite token"
                    >
                      {copied === "token" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                  {inviteLink && (
                    <div className="flex items-center gap-2">
                      <code className="min-w-0 flex-1 truncate rounded-md bg-surface-raised px-2 py-1.5 text-[11px] text-slate-300">
                        {inviteLink}
                      </code>
                      <button
                        type="button"
                        onClick={() => copy(inviteLink, "link")}
                        className="btn-secondary shrink-0 !px-2.5 !py-1.5"
                        title="Copy invite link"
                      >
                        {copied === "link" ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}
