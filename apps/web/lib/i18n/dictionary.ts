/**
 * Shared, statically checked shape for every locale dictionary. Keys are
 * organized by UI domain, not by component, so the same dictionary can be
 * reused across components that render the same concept.
 *
 * Every value is plain, serializable string data — never a function or
 * JSX — so a (sub-)dictionary can be passed as a prop from a Server
 * Component into a Client Component. Strings that need a variable (a page
 * number, a byte count, a quota count, a timestamp) use `{token}`
 * placeholders resolved with `interpolate()` at render time.
 */
export type Dictionary = {
  navigation: {
    homeLinkAriaLabel: string;
    languageSwitcherLabel: string;
    /** `{language}` */
    languageOptionAriaLabel: string;
  };
  footer: {
    tagline: string;
    attribution: string;
    portfolioLink: string;
  };
  home: {
    heading: string;
    subheading: string;
    steps: readonly [
      { step: "1"; title: string; description: string },
      { step: "2"; title: string; description: string },
      { step: "3"; title: string; description: string },
    ];
    /** `{step}` */
    stepLabel: string;
    jsonLdDescription: string;
    motifQuestion: string;
    motifQuote: string;
  };
  upload: {
    dropPrefix: string;
    browse: string;
    sizeHint: string;
    change: string;
    remove: string;
    uploadButton: string;
    uploading: string;
    preparing: string;
    fileInputAriaLabel: string;
    liveUploading: string;
    livePreparing: string;
    errorChooseFile: string;
    errorTooLarge: string;
    errorAlreadyUploadedRetry: string;
    retryPreparation: string;
    errorNetwork: string;
    errorUnexpectedResponse: string;
    errorTooLargeServer: string;
    errorUnsupportedType: string;
    errorProcessingFailed: string;
    errorGeneric: string;
  };
  usage: {
    categoryLabel: Record<"index" | "question" | "analysis", string>;
    /** `{label}`, `{resetTime}` */
    usedUpToday: string;
    /** `{label}`, `{resetTime}` (no reset time known) */
    usedUpTodayNoReset: string;
    /** `{remaining}`, `{limit}`, `{label}` */
    remaining: string;
  };
  document: {
    notFoundHeading: string;
    notFoundBody: string;
    uploadCta: string;
    errorHeading: string;
    errorBody: string;
    tryAgain: string;
    loading: string;
    precomputedDemoTitle: string;
    precomputedDemoBody: string;
    ocrRequiredBody: string;
  };
  status: Record<"parsed" | "ocr_required", string>;
  notFound: {
    heading: string;
    body: string;
    homeCta: string;
  };
  questions: {
    sectionAriaLabel: string;
    preparing: string;
    retryPreparation: string;
    emptyHeading: string;
    emptyBody: string;
    conversationAriaLabel: string;
    jumpToLatest: string;
    composerLabel: string;
    composerPlaceholder: string;
    sendAriaLabel: string;
    askingLive: string;
    enterQuestionError: string;
    citationPageMismatch: string;
    youAskedSr: string;
    insufficientEvidenceTitle: string;
    insufficientEvidenceHint: string;
    thinkingSr: string;
    examplePromptsAriaLabel: string;
    examples: readonly [string, string, string, string];
    sourcesLabel: string;
    /** `{index}` */
    citationLabel: string;
    evidenceCitationsAriaLabel: string;
    /** `{page}` */
    evidencePageLabel: string;
    exampleQuestionSr: string;
    demoQuestionsAriaLabel: string;
    demoBadge: string;
    demoHint: string;
    demoExampleQuestionsAriaLabel: string;
  };
  errors: {
    networkUnavailable: string;
    malformedResponse: string;
    invalidQuestion: string;
    validQuestionRetry: string;
    qaUnavailable: string;
    /** `{time}` */
    resetSuffix: string;
  };
  metadata: {
    titleTemplate: string;
    defaultTitle: string;
    description: string;
    ogAlt: string;
    manifestDescription: string;
  };
  format: {
    /** `{page}` */
    pageSingular: string;
    /** `{start}`, `{end}` */
    pageRange: string;
  };
};
