import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Edit3,
  Globe,
  ListChecks,
  Plug,
  Search,
  Tags,
  Target,
  TrendingUp,
} from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import Badge, { severityTone } from "@/components/Badge";
import { getRankings } from "@/lib/api";
import { DEMO_DOMAIN, DEMO_URL, mockActionPlan, mockCrawlResult, mockRankTrackingSummary } from "@/lib/mock";
import { titleCase } from "@/lib/utils";

const QUICK_LINKS = [
  { href: "/audit", title: "Site Audit", description: "Crawl the site and fix technical issues", icon: Globe },
  { href: "/onpage", title: "On-Page Editor", description: "Score content against SERP competitors", icon: Edit3 },
  { href: "/keywords", title: "Keyword Research", description: "Find volume, difficulty and clusters", icon: Search },
  { href: "/rankings", title: "Rank Tracking", description: "Monitor position changes over time", icon: TrendingUp },
  { href: "/reports", title: "Reports", description: "Generate a white-label client report", icon: BarChart3 },
  { href: "/integrations", title: "Integrations", description: "Leads, CRM and Make.com delivery log", icon: Plug },
];

// Server component: renders on the server, fetches live rankings when the API
// is reachable and falls back to static mock data otherwise (offline demo).
export default async function DashboardPage() {
  let rankings = mockRankTrackingSummary;
  try {
    rankings = await getRankings({ domain: DEMO_DOMAIN });
  } catch {
    // API unavailable — keep the mock fallback assigned above.
  }

  const crawlSummary = mockCrawlResult.summary;
  const plan = mockActionPlan;
  const openTasks = plan.total - (plan.by_status.done ?? 0);

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description={`Overview for ${DEMO_URL.replace("https://", "")} — site health, rankings and open work in one place.`}
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Site Health" value={`${crawlSummary.avg_score}`} icon={<Activity className="h-4 w-4" />} />
        <KpiCard
          label="Avg. Position"
          value={rankings.avg_position.toFixed(1)}
          icon={<Target className="h-4 w-4" />}
          trend={rankings.improved >= rankings.declined ? "up" : "down"}
          trendGood="up"
          trendLabel={`${rankings.improved} up · ${rankings.declined} down`}
        />
        <KpiCard
          label="Tracked Keywords"
          value={`${rankings.total_keywords}`}
          icon={<Tags className="h-4 w-4" />}
          trend="up"
          trendGood="up"
          trendLabel={`${rankings.top10} in top 10`}
        />
        <KpiCard label="Open Tasks" value={`${openTasks}`} icon={<ListChecks className="h-4 w-4" />} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Recent Issues" description="Highest-severity findings from the last crawl" className="lg:col-span-2">
          <ul className="divide-y divide-surface-border">
            {mockCrawlResult.top_issues.map((issue) => (
              <li key={issue.code} className="flex items-start gap-3 py-3 first:pt-0 last:pb-0">
                <Badge tone={severityTone(issue.severity)} className="mt-0.5 shrink-0">
                  {titleCase(issue.severity)}
                </Badge>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-slate-200">{issue.title}</p>
                  <p className="mt-0.5 text-xs text-slate-500">{issue.recommendation}</p>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="This Week" description="Action plan snapshot">
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm">
              <span className="text-slate-400">Total tasks</span>
              <span className="font-semibold text-slate-100">{plan.total}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge tone="neutral">{plan.by_status.todo ?? 0} to do</Badge>
              <Badge tone="info">{plan.by_status.in_progress ?? 0} in progress</Badge>
              <Badge tone="success">{plan.by_status.done ?? 0} done</Badge>
              <Badge tone="warning">{plan.by_status.flagged ?? 0} flagged</Badge>
            </div>
            <Link
              href="/reports"
              className="inline-flex items-center gap-1 text-xs font-medium text-brand-300 transition hover:text-brand-200"
            >
              View full report <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </Card>
      </div>

      <div className="mt-6">
        <h2 className="mb-3 text-sm font-semibold text-slate-300">Jump to a tool</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {QUICK_LINKS.map((link) => {
            const Icon = link.icon;
            return (
              <Link key={link.href} href={link.href} className="group block">
                <Card className="h-full transition hover:border-brand-500/40 hover:bg-surface-raised">
                  <div className="flex items-start justify-between">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-500/10 text-brand-300">
                      <Icon className="h-5 w-5" />
                    </span>
                    <ArrowRight className="h-4 w-4 text-slate-600 transition group-hover:translate-x-0.5 group-hover:text-brand-300" />
                  </div>
                  <p className="mt-3 text-sm font-semibold text-slate-100">{link.title}</p>
                  <p className="mt-1 text-xs text-slate-400">{link.description}</p>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
