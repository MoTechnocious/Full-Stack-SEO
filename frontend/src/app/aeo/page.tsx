"use client";

import { useState, type FormEvent } from "react";
import { Check, CheckCircle2, ClipboardCopy, HelpCircle, Link2, Loader2, Mic, Network, ShieldAlert, XCircle } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import ScoreGauge from "@/components/ScoreGauge";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge from "@/components/Badge";
import {
  ApiError,
  auditVoice,
  buildSchemaGraph,
  extractQuestions,
  mapClusters,
  suggestLinks,
  type ClusterMapResult,
  type FaqEntry,
  type LinkSuggestResult,
  type LinkSuggestion,
  type QuestionExtractionResult,
  type SchemaGraphResult,
  type VoiceAuditResult,
} from "@/lib/api";
import {
  mockClusterMapResult,
  mockLinkSuggestResult,
  mockQuestionExtractionResult,
  mockSchemaGraphResult,
  mockVoiceAuditResult,
} from "@/lib/mock-ai";
import { cn, hostnameOf, truncate } from "@/lib/utils";

const DEMO_SEED = "running shoes";

const DEMO_LINK_PAGES = [
  {
    url: "https://www.example-shop.com/guides/beginner-running-shoes",
    title: "Best Running Shoes for Beginners",
    body: "Guide to the best running shoes for beginners: cushioning, fit, budget and when to replace running shoes.",
  },
  {
    url: "https://www.example-shop.com/guides/when-to-replace-shoes",
    title: "When to Replace Running Shoes",
    body: "How many miles running shoes last, the wear signals to check and the best shoes for new runners.",
  },
  {
    url: "https://www.example-shop.com/blog/marathon-training-plan",
    title: "Marathon Training Plan",
    body: "A 16-week marathon training plan, including when to replace your shoes mid-plan and beginner pacing advice.",
  },
];

const DEMO_VOICE_CONTENT =
  "Most running shoes last between 300 and 500 miles, which is roughly four to six months for someone running twenty miles a week. Track your mileage, check the midsole for creasing, and replace the pair as soon as the cushioning feels flat. Worn-out shoes raise your injury risk because the foam no longer absorbs impact the way it should.";

const DEMO_VOICE_QUESTION = "how long do running shoes last";

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={() => {
        void navigator.clipboard.writeText(text).then(() => {
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        });
      }}
      className="btn-secondary"
    >
      {copied ? <Check className="h-4 w-4 text-emerald-400" /> : <ClipboardCopy className="h-4 w-4" />}
      {copied ? "Copied" : label}
    </button>
  );
}

export default function AeoPage() {
  const [seed, setSeed] = useState(DEMO_SEED);
  const [extraction, setExtraction] = useState<QuestionExtractionResult>(mockQuestionExtractionResult);
  const [extractLoading, setExtractLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(
    "Showing demo data — extract questions for a seed topic to fetch live results.",
  );

  const [clusterMap, setClusterMap] = useState<ClusterMapResult>(mockClusterMapResult);
  const [clusterIsMock, setClusterIsMock] = useState(true);
  const [clusterLoading, setClusterLoading] = useState(false);

  const [schemaGraph, setSchemaGraph] = useState<SchemaGraphResult>(mockSchemaGraphResult);
  const [schemaIsMock, setSchemaIsMock] = useState(true);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [schemaUrl, setSchemaUrl] = useState("https://www.example-shop.com/guides/beginner-running-shoes");
  const [schemaTitle, setSchemaTitle] = useState("Best Running Shoes for Beginners (2026 Guide)");

  const [links, setLinks] = useState<LinkSuggestResult>(mockLinkSuggestResult);
  const [linksAreMock, setLinksAreMock] = useState(true);
  const [linksLoading, setLinksLoading] = useState(false);

  const [voiceContent, setVoiceContent] = useState(DEMO_VOICE_CONTENT);
  const [voiceQuestion, setVoiceQuestion] = useState(DEMO_VOICE_QUESTION);
  const [voice, setVoice] = useState<VoiceAuditResult>(mockVoiceAuditResult);
  const [voiceIsMock, setVoiceIsMock] = useState(true);
  const [voiceLoading, setVoiceLoading] = useState(false);

  async function handleExtract(event: FormEvent) {
    event.preventDefault();
    if (!seed.trim()) return;
    setExtractLoading(true);
    try {
      const data = await extractQuestions({ seed: seed.trim() });
      setExtraction(data);
      setNotice(null);
    } catch (err) {
      setExtraction({ ...mockQuestionExtractionResult, seed: seed.trim() });
      setNotice(
        err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.",
      );
    } finally {
      setExtractLoading(false);
    }
  }

  async function handleClusterMap() {
    setClusterLoading(true);
    try {
      const data = await mapClusters({
        questions: extraction.questions.map((q) => q.question),
        pages: DEMO_LINK_PAGES.map((p) => ({ url: p.url, title: p.title })),
      });
      setClusterMap(data);
      setClusterIsMock(false);
    } catch {
      setClusterMap(mockClusterMapResult);
      setClusterIsMock(true);
    } finally {
      setClusterLoading(false);
    }
  }

  async function handleBuildSchema(event: FormEvent) {
    event.preventDefault();
    if (!schemaUrl.trim() || !schemaTitle.trim()) return;
    setSchemaLoading(true);
    try {
      const data = await buildSchemaGraph({
        url: schemaUrl.trim(),
        title: schemaTitle.trim(),
        faqs: clusterMap.faq.slice(0, 5).map((f) => ({ question: f.question, answer: f.answer_template })),
      });
      setSchemaGraph(data);
      setSchemaIsMock(false);
    } catch {
      setSchemaGraph(mockSchemaGraphResult);
      setSchemaIsMock(true);
    } finally {
      setSchemaLoading(false);
    }
  }

  async function handleSuggestLinks() {
    setLinksLoading(true);
    try {
      const data = await suggestLinks({ pages: DEMO_LINK_PAGES });
      setLinks(data);
      setLinksAreMock(false);
    } catch {
      setLinks(mockLinkSuggestResult);
      setLinksAreMock(true);
    } finally {
      setLinksLoading(false);
    }
  }

  async function handleVoiceAudit(event: FormEvent) {
    event.preventDefault();
    if (!voiceContent.trim()) return;
    setVoiceLoading(true);
    try {
      const data = await auditVoice({ content: voiceContent, question: voiceQuestion.trim() || undefined });
      setVoice(data);
      setVoiceIsMock(false);
    } catch {
      setVoice(mockVoiceAuditResult);
      setVoiceIsMock(true);
    } finally {
      setVoiceLoading(false);
    }
  }

  const faqColumns: Array<DataTableColumn<FaqEntry>> = [
    { key: "question", header: "Question", render: (f) => <span className="block max-w-sm text-slate-200">{f.question}</span> },
    { key: "template", header: "Answer template", render: (f) => <span className="block max-w-md text-xs text-slate-400">{f.answer_template}</span> },
    {
      key: "target",
      header: "Target page",
      render: (f) =>
        f.target_page ? (
          <span className="text-xs text-brand-300">{truncate(f.target_page.replace("https://", ""), 44)}</span>
        ) : (
          <Badge tone="warning">New page needed</Badge>
        ),
    },
  ];

  const linkColumns: Array<DataTableColumn<LinkSuggestion>> = [
    { key: "source", header: "From", render: (l) => <span className="text-xs text-slate-300">{truncate(l.source_url.replace(`https://${hostnameOf(l.source_url)}`, ""), 40)}</span> },
    { key: "target", header: "To", render: (l) => <span className="text-xs text-slate-300">{truncate(l.target_url.replace(`https://${hostnameOf(l.target_url)}`, ""), 40)}</span> },
    { key: "anchor", header: "Anchor text", render: (l) => <span className="font-medium text-slate-200">{l.anchor_text}</span> },
    {
      key: "similarity",
      header: "Similarity",
      render: (l) => <Badge tone={l.similarity >= 0.5 ? "success" : "info"}>{Math.round(l.similarity * 100)}%</Badge>,
    },
  ];

  const schemaJson = JSON.stringify(schemaGraph.json_ld, null, 2);
  const rootQuestions = extraction.questions.filter((q) => q.depth === 0);

  return (
    <div>
      <PageHeader
        title="Answers (AEO)"
        description="Own the question layer: People-Also-Ask exploration, topic clusters, FAQ schema graphs, internal links and voice readiness."
      />

      <Card>
        <form onSubmit={handleExtract} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="aeo-seed" className="label-base">
              Seed topic
            </label>
            <input id="aeo-seed" type="text" value={seed} onChange={(e) => setSeed(e.target.value)} className="input-base" autoComplete="off" />
          </div>
          <button type="submit" disabled={extractLoading} className="btn-primary h-[42px]">
            {extractLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <HelpCircle className="h-4 w-4" />}
            Extract Questions
          </button>
        </form>
        {notice && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-amber-400">
            <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
          </p>
        )}
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card
          title="Question Explorer"
          description={`${extraction.questions.length} People-Also-Ask questions for “${extraction.seed}”`}
          className="xl:col-span-2"
        >
          <ul className="space-y-1.5">
            {extraction.questions.map((q) => (
              <li
                key={q.question}
                className={cn(
                  "flex items-start gap-2 rounded-lg px-3 py-2 text-sm",
                  q.depth === 0 ? "bg-surface-raised/50 font-medium text-slate-200" : "text-slate-300",
                )}
                style={{ marginLeft: q.depth * 20 }}
              >
                <HelpCircle className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", q.depth === 0 ? "text-brand-300" : "text-slate-500")} />
                <span>
                  {q.question}
                  {q.depth > 0 && q.parent && (
                    <span className="ml-2 text-[11px] text-slate-600">follows “{truncate(q.parent, 36)}”</span>
                  )}
                </span>
              </li>
            ))}
          </ul>

          {extraction.autocomplete.length > 0 && (
            <div className="mt-4 border-t border-surface-border pt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Autocomplete pathways</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {extraction.autocomplete.map((s) => (
                  <Badge key={s} tone="neutral">
                    {s}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </Card>

        <Card
          title="Topic Clusters"
          description={clusterIsMock ? "Demo data — cluster the extracted questions" : `${clusterMap.clusters.length} clusters mapped`}
          actions={
            <button type="button" onClick={handleClusterMap} disabled={clusterLoading} className="btn-secondary">
              {clusterLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Network className="h-4 w-4" />}
              Map Clusters
            </button>
          }
        >
          <div className="space-y-4">
            {clusterMap.clusters.map((cluster) => (
              <div key={cluster.label}>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-slate-200">{cluster.label}</p>
                  <span className="text-xs text-slate-500">
                    {cluster.questions.length} question{cluster.questions.length === 1 ? "" : "s"}
                  </span>
                </div>
                <p className="mt-1 text-xs text-slate-400">Primary: {cluster.primary_question}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {cluster.questions.map((q) => (
                    <Badge key={q} tone="neutral">
                      {truncate(q, 40)}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card
        className="mt-6"
        title="FAQ Mapping"
        description={clusterIsMock ? "Demo data — questions matched to their best target page" : "Questions matched to their best target page"}
        padded={false}
      >
        <DataTable columns={faqColumns} data={clusterMap.faq} getRowKey={(f) => f.question} emptyMessage="Map clusters to generate FAQ entries." />
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card
          title="Schema Graph"
          description={schemaIsMock ? "Demo output — combined @graph JSON-LD from your FAQ mapping" : `Node types: ${schemaGraph.node_types.join(", ")}`}
        >
          <form onSubmit={handleBuildSchema} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="aeo-schema-url" className="label-base">
                Page URL
              </label>
              <input id="aeo-schema-url" type="text" value={schemaUrl} onChange={(e) => setSchemaUrl(e.target.value)} className="input-base" />
            </div>
            <div>
              <label htmlFor="aeo-schema-title" className="label-base">
                Page title
              </label>
              <input id="aeo-schema-title" type="text" value={schemaTitle} onChange={(e) => setSchemaTitle(e.target.value)} className="input-base" />
            </div>
            <div className="sm:col-span-2">
              <button type="submit" disabled={schemaLoading} className="btn-primary">
                {schemaLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Network className="h-4 w-4" />}
                Build Schema Graph
              </button>
            </div>
          </form>

          <div className="mt-4">
            <div className="mb-2 flex items-center justify-between gap-2">
              <div className="flex flex-wrap gap-1.5">
                {schemaGraph.node_types.map((t) => (
                  <Badge key={t} tone="brand">
                    {t}
                  </Badge>
                ))}
              </div>
              <CopyButton text={schemaGraph.script_tag} label="Copy script tag" />
            </div>
            <pre className="max-h-72 overflow-auto rounded-xl border border-surface-border bg-surface-raised/60 p-4 text-xs leading-relaxed text-slate-300 scrollbar-thin">
              {schemaJson}
            </pre>
            {schemaGraph.warnings.map((w) => (
              <p key={w} className="mt-2 flex items-center gap-1.5 text-xs text-amber-400">
                <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {w}
              </p>
            ))}
          </div>
        </Card>

        <Card
          title="Internal Link Suggestions"
          description={
            linksAreMock ? "Demo data — similarity-based links between your pages" : `${links.pages_analyzed} pages analyzed`
          }
          actions={
            <button type="button" onClick={handleSuggestLinks} disabled={linksLoading} className="btn-secondary">
              {linksLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Link2 className="h-4 w-4" />}
              Suggest Links
            </button>
          }
          padded={false}
        >
          <DataTable
            columns={linkColumns}
            data={links.suggestions}
            getRowKey={(l) => `${l.source_url}->${l.target_url}`}
            emptyMessage="Analyze your pages to get internal-link suggestions."
          />
        </Card>
      </div>

      <Card
        className="mt-6"
        title="Voice Readiness"
        description={voiceIsMock ? "Demo data — audit a content draft for spoken-answer quality" : `Grade ${voice.grade} — live audit`}
      >
        <form onSubmit={handleVoiceAudit} className="grid grid-cols-1 gap-3 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <label htmlFor="aeo-voice-content" className="label-base">
              Content draft
            </label>
            <textarea
              id="aeo-voice-content"
              value={voiceContent}
              onChange={(e) => setVoiceContent(e.target.value)}
              rows={5}
              className="input-base resize-y"
            />
          </div>
          <div className="flex flex-col gap-3">
            <div>
              <label htmlFor="aeo-voice-question" className="label-base">
                Spoken query it should answer
              </label>
              <input
                id="aeo-voice-question"
                type="text"
                value={voiceQuestion}
                onChange={(e) => setVoiceQuestion(e.target.value)}
                className="input-base"
              />
            </div>
            <button type="submit" disabled={voiceLoading} className="btn-primary">
              {voiceLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Mic className="h-4 w-4" />}
              Audit Voice Readiness
            </button>
          </div>
        </form>

        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="flex flex-col items-center justify-center gap-3">
            <ScoreGauge score={voice.score} label="Voice Score" size={140} />
            <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-slate-400">
              <span>Flesch: <span className="text-slate-200">{voice.flesch.toFixed(1)}</span></span>
              <span>Avg sentence: <span className="text-slate-200">{voice.avg_sentence_length.toFixed(1)}w</span></span>
              <span>Syllables/word: <span className="text-slate-200">{voice.syllable_density.toFixed(2)}</span></span>
              <span>Intro words: <span className="text-slate-200">{voice.first_paragraph_words}</span></span>
            </div>
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Checks</p>
            <ul className="space-y-2">
              {voice.checks.map((check) => (
                <li key={check.code} className="flex items-start gap-2 text-sm">
                  {check.passed ? (
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                  ) : (
                    <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                  )}
                  <div>
                    <p className="text-slate-200">{check.label}</p>
                    <p className="text-xs text-slate-500">{check.message}</p>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Fixes</p>
            <ul className="list-inside list-disc space-y-2 text-sm text-slate-300">
              {voice.fixes.map((fix) => (
                <li key={fix}>{fix}</li>
              ))}
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
