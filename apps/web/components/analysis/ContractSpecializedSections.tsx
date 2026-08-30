import type {
  Clause,
  ContractAnalysis,
  Obligation,
  Party,
  PaymentTerm,
} from "@/lib/analysis-schema";
import { ConfidenceLabel } from "./ConfidenceLabel";
import { EvidenceQuote } from "./EvidenceQuote";

/**
 * Renders only the fields the contract extractor actually returns. This is
 * DocuLens analysis assistance, not legal advice: nothing here labels a
 * clause enforceable, valid, or compliant, and no payment/date value is
 * calculated — every amount/schedule stays the raw text the model cited.
 */
export function ContractSpecializedSections({
  contract,
}: {
  contract: ContractAnalysis;
}) {
  return (
    <div className="flex flex-col gap-8">
      <PartiesSection parties={contract.parties} />
      <ObligationsSection obligations={contract.obligations} />
      <PaymentTermsSection terms={contract.payment_terms} />
      <ClauseGroupSection title="Renewal" clauses={contract.renewal_terms} />
      <ClauseGroupSection title="Termination" clauses={contract.termination_terms} />
      <ClauseGroupSection title="Liability" clauses={contract.liability_terms} />
      <ClauseGroupSection
        title="Confidentiality"
        clauses={contract.confidentiality_terms}
      />
    </div>
  );
}

function PartiesSection({ parties }: { parties: Party[] }) {
  return (
    <section aria-labelledby="contract-parties-heading" className="flex flex-col gap-4">
      <h2 id="contract-parties-heading" className="text-lg font-semibold text-ink">
        Parties
      </h2>
      {parties.length === 0 ? (
        <p className="text-sm text-ink-muted">No parties were identified.</p>
      ) : (
        <ol className="flex flex-col gap-3">
          {parties.map((party) => (
            <li key={party.id} className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-ink">{party.name}</h3>
              {party.role ? (
                <p className="mt-1 text-xs text-ink-subtle">Role: {party.role}</p>
              ) : null}
              <EvidenceQuote page={party.source_page} quote={party.evidence} />
              <div className="mt-2">
                <ConfidenceLabel confidence={party.confidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function ObligationsSection({ obligations }: { obligations: Obligation[] }) {
  return (
    <section
      aria-labelledby="contract-obligations-heading"
      className="flex flex-col gap-4"
    >
      <h2
        id="contract-obligations-heading"
        className="text-lg font-semibold text-ink"
      >
        Obligations
      </h2>
      {obligations.length === 0 ? (
        <p className="text-sm text-ink-muted">No obligations were identified.</p>
      ) : (
        <ol className="flex flex-col gap-3">
          {obligations.map((obligation) => (
            <li
              key={obligation.id}
              className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm"
            >
              <p className="text-sm text-ink-muted">{obligation.description}</p>
              <dl className="mt-1 flex flex-wrap gap-x-6 gap-y-1 text-xs text-ink-muted">
                {obligation.obligated_party ? (
                  <div>
                    <dt className="inline font-medium text-ink">Obligated party: </dt>
                    <dd className="inline">{obligation.obligated_party}</dd>
                  </div>
                ) : null}
                {obligation.beneficiary ? (
                  <div>
                    <dt className="inline font-medium text-ink">Beneficiary: </dt>
                    <dd className="inline">{obligation.beneficiary}</dd>
                  </div>
                ) : null}
              </dl>
              {obligation.conditions.length > 0 ? (
                <ul className="mt-1 list-disc pl-5 text-xs text-ink-muted">
                  {obligation.conditions.map((condition) => (
                    <li key={condition}>{condition}</li>
                  ))}
                </ul>
              ) : null}
              <EvidenceQuote page={obligation.source_page} quote={obligation.evidence} />
              <div className="mt-2">
                <ConfidenceLabel confidence={obligation.confidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function PaymentTermsSection({ terms }: { terms: PaymentTerm[] }) {
  return (
    <section
      aria-labelledby="contract-payment-terms-heading"
      className="flex flex-col gap-4"
    >
      <h2
        id="contract-payment-terms-heading"
        className="text-lg font-semibold text-ink"
      >
        Payment terms
      </h2>
      {terms.length === 0 ? (
        <p className="text-sm text-ink-muted">No payment terms were identified.</p>
      ) : (
        <ol className="flex flex-col gap-3">
          {terms.map((term) => (
            <li key={term.id} className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
              <dl className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-ink-muted">
                {term.payer ? (
                  <div>
                    <dt className="inline font-medium text-ink">Payer: </dt>
                    <dd className="inline">{term.payer}</dd>
                  </div>
                ) : null}
                {term.payee ? (
                  <div>
                    <dt className="inline font-medium text-ink">Payee: </dt>
                    <dd className="inline">{term.payee}</dd>
                  </div>
                ) : null}
                {term.amount_text ? (
                  <div>
                    <dt className="inline font-medium text-ink">Amount: </dt>
                    <dd className="inline">{term.amount_text}</dd>
                  </div>
                ) : null}
                {term.schedule_text ? (
                  <div>
                    <dt className="inline font-medium text-ink">Schedule: </dt>
                    <dd className="inline">{term.schedule_text}</dd>
                  </div>
                ) : null}
              </dl>
              <EvidenceQuote page={term.source_page} quote={term.evidence} />
              <div className="mt-2">
                <ConfidenceLabel confidence={term.confidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function ClauseGroupSection({ title, clauses }: { title: string; clauses: Clause[] }) {
  const headingId = `contract-${title.toLowerCase()}-heading`;
  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-4">
      <h2 id={headingId} className="text-lg font-semibold text-ink">
        {title}
      </h2>
      {clauses.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No {title.toLowerCase()} clause was identified.
        </p>
      ) : (
        <ol className="flex flex-col gap-3">
          {clauses.map((clause) => (
            <li key={clause.id} className="rounded-lg border border-zinc-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-ink">{clause.title}</h3>
              <p className="mt-1 text-sm text-ink-muted">{clause.description}</p>
              {clause.notice_period_text ? (
                <p className="mt-1 text-xs text-ink-muted">
                  Notice period: {clause.notice_period_text}
                </p>
              ) : null}
              {clause.conditions.length > 0 ? (
                <ul className="mt-1 list-disc pl-5 text-xs text-ink-muted">
                  {clause.conditions.map((condition) => (
                    <li key={condition}>{condition}</li>
                  ))}
                </ul>
              ) : null}
              <EvidenceQuote page={clause.source_page} quote={clause.evidence} />
              <div className="mt-2">
                <ConfidenceLabel confidence={clause.confidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
