"use client";

import { useState, type FormEvent } from "react";
import { CheckCircle2, Loader2, ShieldAlert, Sparkles, XCircle } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import ScoreGauge from "@/components/ScoreGauge";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { termStatusTone } from "@/components/Badge";
import {
  ApiError,
  analyzeOnpage,
  contentScore as fetchContentScore,
  type CheckCategory,
  type ContentScore,
  type OnPageCheck,
  type OnPageResult,
  type TermTarget,
} from "@/lib/api";
import { DEMO_TARGET_KEYWORD, mockContentScore, mockOnPageResult } from "@/lib/mock";
import { clampPercent, cn, formatNumber, titleCase } from "@/lib/utils";

const SAMPLE_CONTENT = `Choosing your first pair of running shoes can feel overwhelming. In this guide we cover what beginners should look for, including fit, support and price.

Start by getting properly fitted at a specialty running store. A good pair of running shoes should feel snug in the heel and roomy in the toe box.

Budget matters too. You do not need to spend a fortune to find a great pair of shoes for your first few months of training.`;

const CATEGORY_LABELS: Record<CheckCategory, string> = {
  basic_seo: "Basic SEO",
  additional_seo: "Additional SEO",
  title_readability: "Title Readability",
  content_readability: "Content Readability",
};

const CATEGORY_ORDER: CheckCategory[] = ["basic_seo", "additional_seo", "title_readability", "content_readability"];

function groupChecks(checks: OnPageCheck[]): Array<{ category: CheckCategory; items: OnPageCheck[] }> {
  return CATEGORY_ORDER.map((category) => ({ category, items: checks.filter((check) => check.category === category) })).filter(
    (group) => group.items.length > 0,
  );
}

const termColumns: Array<DataTableColumn<TermTarget>> = [
  { key: "term", header: "Term", render: (term) => <span className="font-medium text-slate-200">{term.term}</span> },
  { key: "current", header: "Current", render: (term) => formatNumber(term.current_count) },
  { key: "target", header: "Target Range", render: (term) => `${term.recommended_min}–${term.recommended_max}` },
  {
    key: "status",
    header: "Status",
    render: (term) => <Badge tone={termStatusTone(term.status)}>{titleCase(term.status)}</Badge>,
  },
  {
    key: "headings",
    header: "In Headings",
    render: (term) => (term.in_headings ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <span className="text-slate-600">—</span>),
  },
];

export default function OnPagePage() {
  const [keyword, setKeyword] = useState(DEMO_TARGET_KEYWORD);
  const [content, setContent] = useState(SAMPLE_CONTENT);
  const [onpage, setOnpage] = useState<OnPageResult>(mockOnPageResult);
  const [score, setScore] = useState<ContentScore>(mockContentScore);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>("Showing demo data — analyze your own content to fetch live results.");

  async function handleAnalyze(event: FormEvent) {
    event.preventDefault();
    if (!keyword.trim()) return;
    setLoading(true);
    let usedMock = false;
    let lastMessage = "";

    try {
      const result = await analyzeOnpage({ target_keyword: keyword.trim(), content });
      setOnpage(result);
    } catch (err) {
      setOnpage(mockOnPageResult);
      usedMock = true;
      lastMessage = err instanceof ApiError ? err.message : "Could not reach the API";
    }

    try {
      const result = await fetchContentScore({ target_keyword: keyword.trim(), content });
      setScore(result);
    } catch (err) {
      setScore(mockContentScore);
      usedMock = true;
      lastMessage = err instanceof ApiError ? err.message : lastMessage || "Could not reach the API";
    }

    setNotice(usedMock ? `${lastMessage} — showing demo data instead.` : null);
    setLoading(false);
  }

  const wordCountPct = clampPercent((score.word_count / Math.max(score.word_count_target_max, 1)) * 100);
  const checkGroups = groupChecks(onpage.checks);

  return (
    <div>
      <PageHeader title="On-Page & Content Editor" description="Score a draft against a Rank Math-style checklist and Surfer-style term targets." />

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-2">
          <form onSubmit={handleAnalyze} className="space-y-4">
            <div>
              <label htmlFor="onpage-keyword" className="label-base">
                Target keyword
              </label>
              <input
                id="onpage-keyword"
                type="text"
                value={keyword}
                onChange={(event) => setKeyword(event.target.value)}
                className="input-base"
                autoComplete="off"
              />
            </div>
            <div>
              <label htmlFor="onpage-content" className="label-base">
                Content draft
              </label>
              <textarea
                id="onpage-content"
                value={content}
                onChange={(event) => setContent(event.target.value)}
                rows={14}
                className="input-base resize-y font-mono text-xs leading-relaxed"
                spellCheck={false}
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              Analyze Content
            </button>
            {notice && (
              <p className="flex items-center gap-1.5 text-xs text-amber-400">
                <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
              </p>
            )}
          </form>
        </Card>

        <div className="space-y-4 xl:col-span-3">
          <Card>
            <div className="flex flex-wrap items-center justify-around gap-6">
              <ScoreGauge score={onpage.score} label={`Grade ${onpage.grade}`} />
              <ScoreGauge score={score.content_score} label="Content Score" />
              <ScoreGauge score={score.seo_score} label="SEO Score" />
            </div>
            <div className="mt-6 border-t border-surface-border pt-4">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span>Word count</span>
                <span className="tabular-nums text-slate-300">
                  {formatNumber(score.word_count)} / {formatNumber(score.word_count_target_min)}-{formatNumber(score.word_count_target_max)}
                </span>
              </div>
              <div className="mt-1.5 h-1.5 w-full rounded-full bg-surface-border">
                <div className="h-1.5 rounded-full bg-gradient-to-r from-brand-500 to-accent-400" style={{ width: `${wordCountPct}%` }} />
              </div>
            </div>
          </Card>

          <Card title="Term Targets" description="Recommended usage bands, derived from top-ranking competitors" padded={false}>
            <DataTable columns={termColumns} data={score.term_targets} getRowKey={(term) => term.term} />
          </Card>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="On-Page Checklist" description={`${onpage.passed_count} of ${onpage.total_count} checks passed`}>
          <div className="space-y-5">
            {checkGroups.map((group) => (
              <div key={group.category}>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{CATEGORY_LABELS[group.category]}</p>
                <ul className="space-y-2">
                  {group.items.map((check) => (
                    <li key={check.code} className="flex items-start gap-2 text-sm">
                      {check.passed ? (
                        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                      ) : (
                        <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                      )}
                      <div>
                        <p className={cn(check.passed ? "text-slate-300" : "text-slate-200")}>{check.label}</p>
                        {check.message && <p className="text-xs text-slate-500">{check.message}</p>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Suggestions" description="What to fix to close the gap with top-ranking pages">
          <div className="space-y-4">
            {score.suggestions.length > 0 && (
              <ul className="space-y-2">
                {score.suggestions.map((suggestion) => (
                  <li key={suggestion} className="flex items-start gap-2 text-sm text-slate-300">
                    <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-400" />
                    {suggestion}
                  </li>
                ))}
              </ul>
            )}
            {score.missing_terms.length > 0 && (
              <div>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Missing terms</p>
                <div className="flex flex-wrap gap-1.5">
                  {score.missing_terms.map((term) => (
                    <Badge key={term} tone="warning">
                      {term}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {score.overused_terms.length > 0 && (
              <div>
                <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-slate-500">Overused terms</p>
                <div className="flex flex-wrap gap-1.5">
                  {score.overused_terms.map((term) => (
                    <Badge key={term} tone="danger">
                      {term}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}
