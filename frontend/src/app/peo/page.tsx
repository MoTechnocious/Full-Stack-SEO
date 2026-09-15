"use client";

import { useState, type FormEvent } from "react";
import { Check, ClipboardCopy, Fingerprint, Loader2, Search, ShieldAlert, UserPlus } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import KpiCard from "@/components/KpiCard";
import ScoreGauge from "@/components/ScoreGauge";
import DataTable, { type DataTableColumn } from "@/components/DataTable";
import Badge, { type BadgeTone } from "@/components/Badge";
import {
  ApiError,
  auditCorroboration,
  buildBio,
  generateEntitySchema,
  getEntitySensor,
  searchEntities,
  trackEntity,
  type BioResult,
  type CorroborationReport,
  type EntitySchemaResult,
  type EntitySearchResult,
  type EntityType,
  type FactComparison,
  type FactStatus,
  type KGEntity,
  type SensorReport,
  type TrendClass,
} from "@/lib/api";
import {
  DEMO_ENTITY_QUERY,
  mockBioResult,
  mockCorroborationReport,
  mockEntitySchemaResult,
  mockEntitySearchResult,
  mockSensorReport,
} from "@/lib/mock-ai";
import { cn, formatNumber, formatSigned, titleCase } from "@/lib/utils";

function trendTone(trend: TrendClass): BadgeTone {
  switch (trend) {
    case "rising":
      return "success";
    case "declining":
      return "danger";
    case "volatile":
      return "warning";
    default:
      return "info";
  }
}

function factStatusTone(status: FactStatus): BadgeTone {
  switch (status) {
    case "match":
      return "success";
    case "mismatch":
      return "danger";
    default:
      return "warning";
  }
}

function Sparkline({ points }: { points: number[] }) {
  if (points.length < 2) return null;
  const width = 260;
  const height = 64;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const coords = points
    .map((value, index) => {
      const x = (index / (points.length - 1)) * (width - 8) + 4;
      const y = height - 6 - ((value - min) / span) * (height - 12);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} className="max-w-full">
      <polyline points={coords} fill="none" stroke="#818cf8" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

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

export default function PeoPage() {
  const [query, setQuery] = useState(DEMO_ENTITY_QUERY);
  const [searchResult, setSearchResult] = useState<EntitySearchResult>(mockEntitySearchResult);
  const [searchLoading, setSearchLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(
    "Showing demo data — search the Knowledge Graph to fetch live results.",
  );

  const [sensor, setSensor] = useState<SensorReport>(mockSensorReport);
  const [sensorIsMock, setSensorIsMock] = useState(true);
  const [trackingMid, setTrackingMid] = useState<string | null>(null);

  const [bioName, setBioName] = useState("Jane Doe");
  const [bioRoles, setBioRoles] = useState("Founder & CEO, angel investor");
  const [bioOrgs, setBioOrgs] = useState("Example Shop");
  const [bioWorks, setBioWorks] = useState("Run Further");
  const [bioCredentials, setBioCredentials] = useState("MBA from Stanford University, Retail Innovator Award 2024");
  const [bioLocation, setBioLocation] = useState("Austin, Texas");
  const [bio, setBio] = useState<BioResult>(mockBioResult);
  const [bioIsMock, setBioIsMock] = useState(true);
  const [bioLoading, setBioLoading] = useState(false);

  const [corroboration, setCorroboration] = useState<CorroborationReport>(mockCorroborationReport);
  const [corroborationIsMock, setCorroborationIsMock] = useState(true);
  const [corroborationLoading, setCorroborationLoading] = useState(false);

  const [schemaType, setSchemaType] = useState<EntityType>("Person");
  const [schemaName, setSchemaName] = useState("Jane Doe");
  const [schemaUrl, setSchemaUrl] = useState("https://www.example-shop.com/about/jane-doe");
  const [schemaJobTitle, setSchemaJobTitle] = useState("Founder & CEO");
  const [schemaWorksFor, setSchemaWorksFor] = useState("Example Shop");
  const [schemaSameAs, setSchemaSameAs] = useState(
    "https://www.linkedin.com/in/janedoe, https://www.wikidata.org/wiki/Q00000000",
  );
  const [entitySchema, setEntitySchema] = useState<EntitySchemaResult>(mockEntitySchemaResult);
  const [schemaIsMock, setSchemaIsMock] = useState(true);
  const [schemaLoading, setSchemaLoading] = useState(false);

  function splitList(value: string): string[] {
    return value
      .split(",")
      .map((v) => v.trim())
      .filter(Boolean);
  }

  async function handleSearch(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setSearchLoading(true);
    try {
      const data = await searchEntities({ query: query.trim() });
      setSearchResult(data);
      setNotice(null);
    } catch (err) {
      setSearchResult({ ...mockEntitySearchResult, query: query.trim() });
      setNotice(
        err instanceof ApiError ? `${err.message} — showing demo data instead.` : "Could not reach the API — showing demo data instead.",
      );
    } finally {
      setSearchLoading(false);
    }
  }

  async function handleTrack(entity: KGEntity) {
    setTrackingMid(entity.kg_mid);
    try {
      await trackEntity({
        kg_mid: entity.kg_mid,
        name: entity.name,
        types: entity.types,
        description: entity.description,
      });
      const report = await getEntitySensor({ kg_mid: entity.kg_mid });
      setSensor(report);
      setSensorIsMock(false);
    } catch {
      setSensor({ ...mockSensorReport, kg_mid: entity.kg_mid, name: entity.name });
      setSensorIsMock(true);
    } finally {
      setTrackingMid(null);
    }
  }

  async function handleBuildBio(event: FormEvent) {
    event.preventDefault();
    if (!bioName.trim()) return;
    setBioLoading(true);
    try {
      const data = await buildBio({
        name: bioName.trim(),
        roles: splitList(bioRoles),
        organizations: splitList(bioOrgs),
        works: splitList(bioWorks),
        credentials: splitList(bioCredentials),
        location: bioLocation.trim() || undefined,
      });
      setBio(data);
      setBioIsMock(false);
    } catch {
      setBio({ ...mockBioResult, name: bioName.trim() });
      setBioIsMock(true);
    } finally {
      setBioLoading(false);
    }
  }

  async function handleCorroborationAudit() {
    setCorroborationLoading(true);
    try {
      const data = await auditCorroboration({
        entity_name: bioName.trim() || "Jane Doe",
        canonical_facts: {
          job_title: splitList(bioRoles)[0] ?? "Founder & CEO",
          organization: splitList(bioOrgs)[0] ?? "Example Shop",
          location: bioLocation.trim() || "Austin, Texas",
        },
        fetch_sources: ["wikipedia", "wikidata", "crunchbase", "linkedin"],
      });
      setCorroboration(data);
      setCorroborationIsMock(false);
    } catch {
      setCorroboration(mockCorroborationReport);
      setCorroborationIsMock(true);
    } finally {
      setCorroborationLoading(false);
    }
  }

  async function handleGenerateSchema(event: FormEvent) {
    event.preventDefault();
    if (!schemaName.trim()) return;
    setSchemaLoading(true);
    try {
      const data = await generateEntitySchema({
        entity_type: schemaType,
        name: schemaName.trim(),
        url: schemaUrl.trim() || undefined,
        job_title: schemaType === "Person" ? schemaJobTitle.trim() || undefined : undefined,
        works_for: schemaType === "Person" ? schemaWorksFor.trim() || undefined : undefined,
        same_as: splitList(schemaSameAs),
      });
      setEntitySchema(data);
      setSchemaIsMock(false);
    } catch {
      setEntitySchema(mockEntitySchemaResult);
      setSchemaIsMock(true);
    } finally {
      setSchemaLoading(false);
    }
  }

  const entityColumns: Array<DataTableColumn<KGEntity>> = [
    {
      key: "name",
      header: "Entity",
      render: (e) => (
        <div>
          <p className="font-medium text-slate-200">{e.name}</p>
          <p className="text-xs text-slate-500">{e.description || e.kg_mid}</p>
        </div>
      ),
    },
    {
      key: "types",
      header: "Types",
      render: (e) => (
        <div className="flex flex-wrap gap-1">
          {e.types.map((t) => (
            <Badge key={t} tone="neutral">
              {t}
            </Badge>
          ))}
        </div>
      ),
    },
    { key: "mid", header: "KGMID", render: (e) => <span className="font-mono text-xs text-slate-400">{e.kg_mid}</span> },
    { key: "score", header: "Score", render: (e) => <span className="tabular-nums text-slate-200">{e.result_score.toFixed(1)}</span> },
    {
      key: "actions",
      header: "",
      render: (e) => (
        <button
          type="button"
          onClick={() => handleTrack(e)}
          disabled={trackingMid === e.kg_mid}
          className="inline-flex items-center gap-1 text-xs font-medium text-brand-300 transition hover:text-brand-200"
        >
          {trackingMid === e.kg_mid ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <UserPlus className="h-3.5 w-3.5" />}
          Track
        </button>
      ),
    },
  ];

  const comparisonColumns: Array<DataTableColumn<FactComparison>> = [
    { key: "source", header: "Source", render: (c) => <span className="text-slate-300">{titleCase(c.source)}</span> },
    { key: "fact", header: "Fact", render: (c) => <span className="text-slate-300">{titleCase(c.fact)}</span> },
    { key: "canonical", header: "Canonical", render: (c) => <span className="text-slate-200">{c.canonical_value}</span> },
    { key: "found", header: "Found", render: (c) => <span className="text-slate-400">{c.found_value ?? "—"}</span> },
    { key: "status", header: "Status", render: (c) => <Badge tone={factStatusTone(c.status)} dot>{titleCase(c.status)}</Badge> },
  ];

  const schemaJson = JSON.stringify(entitySchema.json_ld, null, 2);

  return (
    <div>
      <PageHeader
        title="Entity (PEO)"
        description="Claim and strengthen your Knowledge Graph presence: entity tracking, NLP-optimized bios, cross-source corroboration and entity schema."
      />

      <Card>
        <form onSubmit={handleSearch} className="flex flex-col gap-3 sm:flex-row sm:items-end">
          <div className="flex-1">
            <label htmlFor="peo-query" className="label-base">
              Entity name
            </label>
            <input id="peo-query" type="text" value={query} onChange={(e) => setQuery(e.target.value)} className="input-base" autoComplete="off" />
          </div>
          <button type="submit" disabled={searchLoading} className="btn-primary h-[42px]">
            {searchLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            Search Knowledge Graph
          </button>
        </form>
        {notice && (
          <p className="mt-3 flex items-center gap-1.5 text-xs text-amber-400">
            <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {notice}
          </p>
        )}
      </Card>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card title="Knowledge Graph Matches" description="Track an entity to start the KG sensor" className="xl:col-span-2" padded={false}>
          <DataTable columns={entityColumns} data={searchResult.entities} getRowKey={(e) => e.kg_mid} emptyMessage="Search for a person or organization to see KG candidates." />
        </Card>

        <Card
          title="KG Sensor"
          description={sensorIsMock ? "Demo data — track an entity for a live series" : `Confidence series for ${sensor.name}`}
        >
          <div className="flex items-center justify-between gap-2">
            <div>
              <p className="text-sm font-semibold text-slate-100">{sensor.name || sensor.kg_mid}</p>
              <p className="font-mono text-xs text-slate-500">{sensor.kg_mid}</p>
            </div>
            <Badge tone={trendTone(sensor.trend)} dot>
              {titleCase(sensor.trend)}
            </Badge>
          </div>
          <div className="mt-3">
            <Sparkline points={sensor.observations.map((o) => o.score)} />
          </div>
          <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Latest</dt>
              <dd className="mt-0.5 font-semibold text-slate-100 tabular-nums">{sensor.latest_score.toFixed(1)}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Mean</dt>
              <dd className="mt-0.5 font-semibold text-slate-100 tabular-nums">{sensor.mean_score.toFixed(1)}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Net change</dt>
              <dd
                className={cn(
                  "mt-0.5 font-semibold tabular-nums",
                  sensor.net_change > 0 ? "text-emerald-400" : sensor.net_change < 0 ? "text-rose-400" : "text-slate-100",
                )}
              >
                {formatSigned(Math.round(sensor.net_change * 10) / 10)}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-500">Volatility</dt>
              <dd className="mt-0.5 font-semibold text-slate-100 tabular-nums">{sensor.volatility.toFixed(1)}</dd>
            </div>
          </dl>
        </Card>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 xl:grid-cols-2">
        <Card title="Bio Builder" description="Structured facts in, NLP-optimized entity bios out">
          <form onSubmit={handleBuildBio} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="bio-name" className="label-base">
                Name
              </label>
              <input id="bio-name" type="text" value={bioName} onChange={(e) => setBioName(e.target.value)} className="input-base" />
            </div>
            <div>
              <label htmlFor="bio-location" className="label-base">
                Location
              </label>
              <input id="bio-location" type="text" value={bioLocation} onChange={(e) => setBioLocation(e.target.value)} className="input-base" />
            </div>
            <div>
              <label htmlFor="bio-roles" className="label-base">
                Roles (comma-separated)
              </label>
              <input id="bio-roles" type="text" value={bioRoles} onChange={(e) => setBioRoles(e.target.value)} className="input-base" />
            </div>
            <div>
              <label htmlFor="bio-orgs" className="label-base">
                Organizations
              </label>
              <input id="bio-orgs" type="text" value={bioOrgs} onChange={(e) => setBioOrgs(e.target.value)} className="input-base" />
            </div>
            <div>
              <label htmlFor="bio-works" className="label-base">
                Notable works
              </label>
              <input id="bio-works" type="text" value={bioWorks} onChange={(e) => setBioWorks(e.target.value)} className="input-base" />
            </div>
            <div>
              <label htmlFor="bio-credentials" className="label-base">
                Credentials
              </label>
              <input id="bio-credentials" type="text" value={bioCredentials} onChange={(e) => setBioCredentials(e.target.value)} className="input-base" />
            </div>
            <div className="sm:col-span-2">
              <button type="submit" disabled={bioLoading} className="btn-primary">
                {bioLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Fingerprint className="h-4 w-4" />}
                Build Bios
              </button>
            </div>
          </form>

          <div className="mt-5 space-y-3">
            {bioIsMock && <p className="text-xs text-slate-500">Demo output — build bios from your facts for live results.</p>}
            {bio.variants.map((variant) => (
              <div key={variant.length} className="rounded-xl border border-surface-border bg-surface-raised/40 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge tone="brand">{titleCase(variant.length)}</Badge>
                    <span className="text-xs text-slate-500">
                      {variant.word_count} words · {variant.triple_count} facts · {variant.triple_density.toFixed(2)} facts/sentence
                    </span>
                  </div>
                  <CopyButton text={variant.text} />
                </div>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">{variant.text}</p>
              </div>
            ))}
            {bio.warnings.map((warning) => (
              <p key={warning} className="flex items-center gap-1.5 text-xs text-amber-400">
                <ShieldAlert className="h-3.5 w-3.5 shrink-0" /> {warning}
              </p>
            ))}
          </div>
        </Card>

        <Card
          title="Corroboration Audit"
          description={
            corroborationIsMock
              ? "Demo data — diff your canonical facts against Wikipedia, Wikidata, Crunchbase and LinkedIn"
              : `${corroboration.sources_checked} sources checked for ${corroboration.entity_name}`
          }
          actions={
            <button type="button" onClick={handleCorroborationAudit} disabled={corroborationLoading} className="btn-secondary">
              {corroborationLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
              Run Audit
            </button>
          }
          padded={false}
        >
          <div className="flex flex-wrap items-center gap-6 px-5 py-4">
            <ScoreGauge score={corroboration.consistency_score} label="Consistency" size={110} strokeWidth={9} />
            <div className="flex flex-wrap gap-2">
              <Badge tone="success" dot>
                {corroboration.match_count} match
              </Badge>
              <Badge tone="danger" dot>
                {corroboration.mismatch_count} mismatch
              </Badge>
              <Badge tone="warning" dot>
                {corroboration.missing_count} missing
              </Badge>
            </div>
          </div>
          <DataTable
            columns={comparisonColumns}
            data={corroboration.comparisons}
            getRowKey={(c, index) => `${c.source}-${c.fact}-${index}`}
            emptyMessage="Run an audit to compare sources."
          />
          {corroboration.fixes.length > 0 && (
            <div className="border-t border-surface-border px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Suggested fixes</p>
              <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-slate-300">
                {corroboration.fixes.map((fix) => (
                  <li key={fix}>{fix}</li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      </div>

      <Card
        className="mt-6"
        title="Entity JSON-LD"
        description={schemaIsMock ? "Demo output — generate relationally-linked Person/Organization schema" : `Generated ${entitySchema.entity_type} schema`}
      >
        <form onSubmit={handleGenerateSchema} className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <div>
            <label htmlFor="schema-type" className="label-base">
              Entity type
            </label>
            <select id="schema-type" value={schemaType} onChange={(e) => setSchemaType(e.target.value as EntityType)} className="input-base">
              <option value="Person">Person</option>
              <option value="Organization">Organization</option>
            </select>
          </div>
          <div>
            <label htmlFor="schema-name" className="label-base">
              Name
            </label>
            <input id="schema-name" type="text" value={schemaName} onChange={(e) => setSchemaName(e.target.value)} className="input-base" />
          </div>
          <div>
            <label htmlFor="schema-url" className="label-base">
              URL
            </label>
            <input id="schema-url" type="text" value={schemaUrl} onChange={(e) => setSchemaUrl(e.target.value)} className="input-base" />
          </div>
          {schemaType === "Person" && (
            <>
              <div>
                <label htmlFor="schema-job" className="label-base">
                  Job title
                </label>
                <input id="schema-job" type="text" value={schemaJobTitle} onChange={(e) => setSchemaJobTitle(e.target.value)} className="input-base" />
              </div>
              <div>
                <label htmlFor="schema-worksfor" className="label-base">
                  Works for
                </label>
                <input id="schema-worksfor" type="text" value={schemaWorksFor} onChange={(e) => setSchemaWorksFor(e.target.value)} className="input-base" />
              </div>
            </>
          )}
          <div className={schemaType === "Person" ? "" : "sm:col-span-2 xl:col-span-1"}>
            <label htmlFor="schema-sameas" className="label-base">
              sameAs profiles (comma-separated)
            </label>
            <input id="schema-sameas" type="text" value={schemaSameAs} onChange={(e) => setSchemaSameAs(e.target.value)} className="input-base" />
          </div>
          <div className="sm:col-span-2 xl:col-span-3">
            <button type="submit" disabled={schemaLoading} className="btn-primary">
              {schemaLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Fingerprint className="h-4 w-4" />}
              Generate JSON-LD
            </button>
          </div>
        </form>

        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="flex flex-wrap gap-1.5">
              <Badge tone="brand">{entitySchema.entity_type}</Badge>
              {entitySchema.warnings.map((w) => (
                <Badge key={w} tone="warning">
                  {w}
                </Badge>
              ))}
            </div>
            <CopyButton text={entitySchema.script_tag} label="Copy script tag" />
          </div>
          <pre className="max-h-96 overflow-auto rounded-xl border border-surface-border bg-surface-raised/60 p-4 text-xs leading-relaxed text-slate-300 scrollbar-thin">
            {schemaJson}
          </pre>
        </div>
      </Card>
    </div>
  );
}
