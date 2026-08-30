import type {
  Requirement,
  TechnicalConstraint,
  TechnicalDependency,
  TechnicalSpecAnalysis,
} from "@/lib/analysis-schema";
import { ConfidenceLabel } from "./ConfidenceLabel";
import { EvidenceQuote } from "./EvidenceQuote";
import { PriorityBadge } from "./PriorityBadge";

const CONSTRAINT_CATEGORY_LABELS: Record<TechnicalConstraint["category"], string> = {
  technology: "Technology",
  performance: "Performance",
  deployment: "Deployment",
  compatibility: "Compatibility",
};

/**
 * Renders only the fields the technical-specification extractor actually
 * returns. This is analysis assistance, not proof that a requirement is
 * implemented, tested, compliant, or complete.
 */
export function TechnicalSpecSpecializedSections({
  spec,
}: {
  spec: TechnicalSpecAnalysis;
}) {
  return (
    <div className="flex flex-col gap-8">
      <RequirementGroupSection
        title="Functional requirements"
        requirements={spec.functional_requirements}
      />
      <RequirementGroupSection
        title="Non-functional requirements"
        requirements={spec.non_functional_requirements}
      />
      <RequirementGroupSection
        title="Security requirements"
        requirements={spec.security_requirements}
      />
      <RequirementGroupSection
        title="Integration requirements"
        requirements={spec.integration_requirements}
      />
      <ConstraintsSection constraints={spec.constraints} />
      <DependenciesSection dependencies={spec.dependencies} />
    </div>
  );
}

function RequirementGroupSection({
  title,
  requirements,
}: {
  title: string;
  requirements: Requirement[];
}) {
  const headingId = `requirement-${title.toLowerCase().replace(/\s+/g, "-")}-heading`;
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-4">
      <h2 id={headingId} className="text-lg font-semibold text-ink">
        {title}
      </h2>
      {requirements.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No {title.toLowerCase()} were identified.
        </p>
      ) : (
        <ol className="flex flex-col gap-3">
          {requirements.map((requirement) => (
            <li
              key={requirement.id}
              className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="text-sm font-semibold text-ink">
                  {requirement.identifier ? `${requirement.identifier}: ` : ""}
                  {requirement.statement}
                </h3>
                <PriorityBadge priority={requirement.priority} />
              </div>
              <dl className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-xs text-ink-muted">
                {requirement.actor ? (
                  <div>
                    <dt className="inline font-medium text-ink">Actor: </dt>
                    <dd className="inline">{requirement.actor}</dd>
                  </div>
                ) : null}
                {requirement.measurable_criterion ? (
                  <div>
                    <dt className="inline font-medium text-ink">Criterion: </dt>
                    <dd className="inline">{requirement.measurable_criterion}</dd>
                  </div>
                ) : null}
              </dl>
              <EvidenceQuote page={requirement.source_page} quote={requirement.evidence} />
              <div className="mt-2">
                <ConfidenceLabel confidence={requirement.confidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function ConstraintsSection({ constraints }: { constraints: TechnicalConstraint[] }) {
  return (
    <section aria-labelledby="constraints-heading" className="flex flex-col gap-4">
      <h2 id="constraints-heading" className="text-lg font-semibold text-ink">
        Constraints
      </h2>
      {constraints.length === 0 ? (
        <p className="text-sm text-ink-muted">No constraints were identified.</p>
      ) : (
        <ol className="flex flex-col gap-3">
          {constraints.map((constraint) => (
            <li
              key={constraint.id}
              className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="text-sm text-ink-muted">{constraint.statement}</p>
                <span className="inline-flex items-center rounded-full bg-zinc-100 px-2.5 py-1 text-xs font-medium text-ink-muted ring-1 ring-inset ring-zinc-500/20">
                  {CONSTRAINT_CATEGORY_LABELS[constraint.category]}
                </span>
              </div>
              {constraint.value_text ? (
                <p className="mt-1 text-xs text-ink-muted">Value: {constraint.value_text}</p>
              ) : null}
              <EvidenceQuote page={constraint.source_page} quote={constraint.evidence} />
              <div className="mt-2">
                <ConfidenceLabel confidence={constraint.confidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function DependenciesSection({ dependencies }: { dependencies: TechnicalDependency[] }) {
  return (
    <section aria-labelledby="dependencies-heading" className="flex flex-col gap-4">
      <h2 id="dependencies-heading" className="text-lg font-semibold text-ink">
        Dependencies
      </h2>
      {dependencies.length === 0 ? (
        <p className="text-sm text-ink-muted">No dependencies were identified.</p>
      ) : (
        <ol className="flex flex-col gap-3">
          {dependencies.map((dependency) => (
            <li
              key={dependency.id}
              className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm"
            >
              <h3 className="text-sm font-semibold text-ink">{dependency.name}</h3>
              {dependency.dependency_type ? (
                <p className="mt-1 text-xs text-ink-subtle">{dependency.dependency_type}</p>
              ) : null}
              <p className="mt-2 text-sm text-ink-muted">{dependency.description}</p>
              <EvidenceQuote page={dependency.source_page} quote={dependency.evidence} />
              <div className="mt-2">
                <ConfidenceLabel confidence={dependency.confidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
