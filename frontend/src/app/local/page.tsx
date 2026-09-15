"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Loader2, Lock, LockOpen, MapPin, MessageSquareReply, RefreshCw, Send, Star } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { type BadgeTone } from "@/components/Badge";
import {
  getCitationStatus,
  getGbpMetrics,
  getGbpReviews,
  getNap,
  publishGbpPost,
  putNap,
  replyToReview,
  syncCitations,
  type CitationStatusReport,
  type CitationSyncReport,
  type DirectoryStatus,
  type GbpMetrics,
  type GbpPost,
  type ListingDeliveryState,
  type NapRecord,
  type ReviewListResponse,
} from "@/lib/api";
import { mockCitationStatusReport, mockGbpMetrics, mockNapRecord, mockReviewList } from "@/lib/mock-ai";
import { formatDate, formatNumber, titleCase } from "@/lib/utils";

const DIRECTORY_LABELS: Record<string, string> = {
  yelp: "Yelp",
  apple_maps: "Apple Maps",
  bing_places: "Bing Places",
  foursquare: "Foursquare",
};

function deliveryTone(state: ListingDeliveryState): BadgeTone {
  switch (state) {
    case "in_sync":
    case "created":
    case "updated":
      return "success";
    case "drift_flagged":
      return "warning";
    case "failed":
    case "drift_blocked":
      return "danger";
    default:
      return "neutral";
  }
}

function ratingStars(rating: number): string {
  return "★".repeat(Math.round(rating)) + "☆".repeat(5 - Math.round(rating));
}

export default function LocalSeoPage() {
  const [metrics, setMetrics] = useState<GbpMetrics>(mockGbpMetrics);
  const [reviews, setReviews] = useState<ReviewListResponse>(mockReviewList);
  const [nap, setNap] = useState<NapRecord>(mockNapRecord);
  const [status, setStatus] = useState<CitationStatusReport>(mockCitationStatusReport);
  const [notice, setNotice] = useState<string | null>(
    "Showing demo data — connect the API to manage your live Google Business Profile and citations.",
  );

  const [postSummary, setPostSummary] = useState("");
  const [postTopic, setPostTopic] = useState("update");
  const [postCta, setPostCta] = useState("");
  const [publishing, setPublishing] = useState(false);
  const [lastPost, setLastPost] = useState<GbpPost | null>(null);

  const [replyingTo, setReplyingTo] = useState<string | null>(null);
  const [savingNap, setSavingNap] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [syncReport, setSyncReport] = useState<CitationSyncReport | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [m, r, n, s] = await Promise.all([
          getGbpMetrics(),
          getGbpReviews(),
          getNap(),
          getCitationStatus(),
        ]);
        if (cancelled) return;
        setMetrics(m);
        setReviews(r);
        setNap(n);
        setStatus(s);
        setNotice(null);
      } catch {
        /* keep demo data */
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handlePublish(event: FormEvent) {
    event.preventDefault();
    if (!postSummary.trim()) return;
    setPublishing(true);
    try {
      const post = await publishGbpPost({
        summary: postSummary.trim(),
        topic: postTopic,
        cta_url: postCta.trim() || undefined,
      });
      setLastPost(post);
      setPostSummary("");
      setPostCta("");
      setNotice(null);
    } catch {
      setNotice("Could not publish — API unavailable, still showing demo data.");
    } finally {
      setPublishing(false);
    }
  }

  async function handleReply(reviewId: string) {
    setReplyingTo(reviewId);
    try {
      const updated = await replyToReview(reviewId);
      setReviews((prev) => ({
        ...prev,
        reviews: prev.reviews.map((r) => (r.id === updated.id ? updated : r)),
      }));
    } catch {
      const suggestion = reviews.suggested_replies.find((s) => s.review_id === reviewId);
      setReviews((prev) => ({
        ...prev,
        reviews: prev.reviews.map((r) =>
          r.id === reviewId ? { ...r, reply: suggestion?.text ?? "Thank you for your feedback!" } : r,
        ),
      }));
    } finally {
      setReplyingTo(null);
    }
  }

  async function handleSaveNap(event: FormEvent) {
    event.preventDefault();
    setSavingNap(true);
    try {
      const saved = await putNap(nap);
      setNap(saved);
      setNotice(null);
    } catch {
      setNotice("Could not save NAP — API unavailable, changes kept locally.");
    } finally {
      setSavingNap(false);
    }
  }

  async function handleSync() {
    setSyncing(true);
    try {
      const report = await syncCitations();
      setSyncReport(report);
      const fresh = await getCitationStatus();
      setStatus(fresh);
      setNotice(null);
    } catch {
      setNotice("Sync unavailable — showing demo citation status.");
    } finally {
      setSyncing(false);
    }
  }

  const directoryColumns: Array<DataTableColumn<DirectoryStatus>> = [
    {
      key: "directory",
      header: "Directory",
      render: (d) => (
        <span className="font-medium text-slate-200">{DIRECTORY_LABELS[d.directory] ?? titleCase(d.directory)}</span>
      ),
    },
    {
      key: "listed",
      header: "Listed",
      render: (d) => (
        <Badge tone={d.listed ? "success" : "neutral"} dot>
          {d.listed ? "Listed" : "Not listed"}
        </Badge>
      ),
    },
    {
      key: "state",
      header: "State",
      render: (d) => (
        <Badge tone={deliveryTone(d.state)} dot>
          {titleCase(d.state)}
        </Badge>
      ),
    },
    {
      key: "diffs",
      header: "NAP Drift",
      render: (d) =>
        d.diffs.length === 0 ? (
          <span className="text-xs text-slate-500">None</span>
        ) : (
          <div className="space-y-0.5">
            {d.diffs.map((diff) => (
              <p key={diff.field} className="text-xs text-amber-300">
                {titleCase(diff.field)}: found “{diff.found}” — expected “{diff.expected}”
              </p>
            ))}
          </div>
        ),
    },
  ];

  const totalViews = metrics.views_search + metrics.views_maps;
  const totalActions = metrics.actions_website + metrics.actions_calls + metrics.actions_directions;

  return (
    <div>
      <PageHeader
        title="Local SEO"
        description="Publish Google Business Profile updates, track local metrics, answer reviews, and keep your NAP locked and consistent across directories."
      />

      {notice ? (
        <p className="mb-4 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-2.5 text-xs text-amber-200">{notice}</p>
      ) : null}

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label={`Profile Views (${metrics.period_days}d)`} value={formatNumber(totalViews)} />
        <KpiCard label="Direct Searches" value={formatNumber(metrics.searches_direct)} />
        <KpiCard label="Discovery Searches" value={formatNumber(metrics.searches_discovery)} />
        <KpiCard label="Customer Actions" value={formatNumber(totalActions)} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Publish a GBP Update" description="Posts go straight to your Business Profile via the connected provider.">
          <form onSubmit={handlePublish} className="space-y-3">
            <div>
              <label htmlFor="gbp-summary" className="label-base">
                Update text
              </label>
              <textarea
                id="gbp-summary"
                value={postSummary}
                onChange={(e) => setPostSummary(e.target.value)}
                rows={3}
                className="input-base"
                placeholder="Summer fitting event this Saturday — free gait analysis for every visitor."
              />
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="gbp-topic" className="label-base">
                  Topic
                </label>
                <select id="gbp-topic" value={postTopic} onChange={(e) => setPostTopic(e.target.value)} className="input-base">
                  <option value="update">Update</option>
                  <option value="offer">Offer</option>
                  <option value="event">Event</option>
                </select>
              </div>
              <div>
                <label htmlFor="gbp-cta" className="label-base">
                  CTA link (optional)
                </label>
                <input
                  id="gbp-cta"
                  value={postCta}
                  onChange={(e) => setPostCta(e.target.value)}
                  className="input-base"
                  placeholder="https://…"
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={publishing || !postSummary.trim()}>
              {publishing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              Publish update
            </button>
            {lastPost ? (
              <p className="text-xs text-emerald-300">
                Published “{lastPost.summary.slice(0, 60)}…” — state: {titleCase(lastPost.state)}
              </p>
            ) : null}
          </form>
        </Card>

        <Card
          title="Canonical NAP Record"
          description="The single source of truth distributed to every directory."
          actions={
            <button
              type="button"
              onClick={() => setNap((prev) => ({ ...prev, locked: !prev.locked }))}
              className="btn-secondary"
              title={nap.locked ? "NAP locked — drift is flagged/blocked" : "NAP unlocked"}
            >
              {nap.locked ? <Lock className="h-4 w-4" /> : <LockOpen className="h-4 w-4" />}
              {nap.locked ? "Locked" : "Unlocked"}
            </button>
          }
        >
          <form onSubmit={handleSaveNap} className="space-y-3">
            <div>
              <label htmlFor="nap-name" className="label-base">
                Business name
              </label>
              <input id="nap-name" value={nap.name} onChange={(e) => setNap({ ...nap, name: e.target.value })} className="input-base" />
            </div>
            <div>
              <label htmlFor="nap-address" className="label-base">
                Address
              </label>
              <input
                id="nap-address"
                value={nap.address}
                onChange={(e) => setNap({ ...nap, address: e.target.value })}
                className="input-base"
              />
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="nap-phone" className="label-base">
                  Phone
                </label>
                <input id="nap-phone" value={nap.phone} onChange={(e) => setNap({ ...nap, phone: e.target.value })} className="input-base" />
              </div>
              <div>
                <label htmlFor="nap-website" className="label-base">
                  Website
                </label>
                <input
                  id="nap-website"
                  value={nap.website ?? ""}
                  onChange={(e) => setNap({ ...nap, website: e.target.value || null })}
                  className="input-base"
                />
              </div>
            </div>
            <button type="submit" className="btn-primary" disabled={savingNap}>
              {savingNap ? <Loader2 className="h-4 w-4 animate-spin" /> : <MapPin className="h-4 w-4" />}
              Save NAP
            </button>
          </form>
        </Card>
      </div>

      <div className="mt-6">
        <Card
          title="Citation Sync"
          description={
            status.drift_detected
              ? "Drift detected — one or more directories disagree with your canonical NAP."
              : "All directories match your canonical NAP."
          }
          padded={false}
          actions={
            <button type="button" onClick={handleSync} className="btn-primary" disabled={syncing}>
              {syncing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
              Sync all directories
            </button>
          }
        >
          <DataTable columns={directoryColumns} data={status.directories} getRowKey={(d) => d.directory} emptyMessage="No directories configured." />
          {syncReport ? (
            <p className="border-t border-surface-border px-4 py-2.5 text-xs text-slate-400">
              Last sync: {formatNumber(syncReport.delivered)} delivered, {formatNumber(syncReport.failed)} failed.
            </p>
          ) : null}
        </Card>
      </div>

      <div className="mt-6">
        <Card title="Reviews" description="Latest Google reviews with AI-suggested replies." padded={false}>
          <ul className="divide-y divide-surface-border">
            {reviews.reviews.map((review) => {
              const suggestion = reviews.suggested_replies.find((s) => s.review_id === review.id);
              return (
                <li key={review.id} className="px-4 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-slate-200">{review.author}</span>
                    <span className="text-xs text-amber-300" aria-label={`${review.rating} stars`}>
                      <Star className="mr-0.5 inline h-3 w-3" />
                      {ratingStars(review.rating)}
                    </span>
                    <span className="text-xs text-slate-500">{formatDate(review.created_at)}</span>
                    {suggestion ? (
                      <Badge tone={suggestion.sentiment === "negative" ? "danger" : suggestion.sentiment === "positive" ? "success" : "neutral"} dot>
                        {titleCase(suggestion.sentiment)}
                      </Badge>
                    ) : null}
                  </div>
                  <p className="mt-1.5 text-sm text-slate-400">{review.text}</p>
                  {review.reply ? (
                    <p className="mt-2 rounded-lg border border-brand-500/20 bg-brand-500/5 px-3 py-2 text-xs text-brand-200">
                      Your reply: {review.reply}
                    </p>
                  ) : suggestion ? (
                    <div className="mt-2 flex flex-col gap-2 rounded-lg border border-surface-border bg-white/[0.02] px-3 py-2 sm:flex-row sm:items-center">
                      <p className="flex-1 text-xs text-slate-400">
                        <span className="font-medium text-slate-300">Suggested reply:</span> {suggestion.text}
                      </p>
                      <button
                        type="button"
                        onClick={() => handleReply(review.id)}
                        className="btn-secondary shrink-0"
                        disabled={replyingTo === review.id}
                      >
                        {replyingTo === review.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <MessageSquareReply className="h-4 w-4" />
                        )}
                        Send reply
                      </button>
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ul>
        </Card>
      </div>
    </div>
  );
}
