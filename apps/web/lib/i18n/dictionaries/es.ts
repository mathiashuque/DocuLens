import type { Dictionary } from "../dictionary";

const es: Dictionary = {
  navigation: {
    homeLinkAriaLabel: "Inicio de DocuLens",
    languageSwitcherLabel: "Idioma",
    languageOptionAriaLabel: "Cambiar idioma a {language}",
  },
  home: {
    heading: "Comprende documentos complejos con evidencia, no con suposiciones.",
    subheading:
      "Sube un documento y pregúntale lo que quieras: preguntas factuales, análisis de riesgos, extracción de obligaciones, plazos, comparaciones o resúmenes. Cada respuesta está fundamentada en este documento y se puede rastrear hasta la página y la cita exactas de donde proviene.",
    steps: [
      {
        step: "1",
        title: "Sube el documento",
        description: "Sube un PDF. Se prepara automáticamente para preguntas fundamentadas en evidencia.",
      },
      {
        step: "2",
        title: "Pregunta o analiza",
        description:
          "Haz una pregunta directa o solicita un análisis: riesgos, obligaciones, plazos, comparaciones, resúmenes.",
      },
      {
        step: "3",
        title: "Revisa la evidencia",
        description: "Cada respuesta cita la página y la cita exactas de donde proviene, o lo indica cuando no puede.",
      },
    ],
    stepLabel: "Paso {step}",
    jsonLdDescription:
      "Sube un PDF y luego hazle preguntas o solicita un análisis fundamentado en la página y la cita exactas de donde proviene.",
    motifQuestion: "¿Qué pasa si alguna de las partes quiere terminar esto antes de tiempo?",
    motifQuote: "…cualquiera de las partes puede rescindir con sesenta días de preaviso por escrito…",
  },
  upload: {
    dropPrefix: "Suelta un PDF aquí, o",
    browse: "explora tus archivos",
    sizeHint: "Hasta 10 MB",
    change: "Cambiar",
    remove: "Quitar",
    uploadButton: "Subir documento",
    uploading: "Subiendo…",
    preparing: "Preparando…",
    fileInputAriaLabel: "Documento PDF",
    liveUploading: "Subiendo documento.",
    livePreparing: "Preparando el documento para preguntas.",
    errorChooseFile: "Elige un archivo PDF.",
    errorTooLarge: "Ese archivo pesa más de 10 MB.",
    errorAlreadyUploadedRetry: "Tu archivo ya está subido; reintentar solo reanuda la preparación.",
    retryPreparation: "Reintentar preparación",
    errorNetwork: "No se pudo contactar el servicio de subida. Verifica tu conexión e inténtalo de nuevo.",
    errorUnexpectedResponse: "El servicio de subida devolvió una respuesta inesperada.",
    errorTooLargeServer: "Ese archivo es demasiado grande. Sube un PDF de menos de 10 MB.",
    errorUnsupportedType: "Ese tipo de archivo no es compatible. Sube un PDF.",
    errorProcessingFailed: "No se pudo procesar el PDF. Puede estar cifrado o dañado.",
    errorGeneric: "Algo salió mal al subir el documento. Inténtalo de nuevo.",
  },
  usage: {
    categoryLabel: {
      index: "subidas de documentos",
      question: "preguntas",
      analysis: "análisis",
    },
    usedUpToday: "Ya usaste tus {label} gratuitas de hoy — más disponibles a las {resetTime}.",
    usedUpTodayNoReset: "Ya usaste tus {label} gratuitas de hoy.",
    remaining: "{remaining} de {limit} {label} gratuitas disponibles hoy",
  },
  document: {
    notFoundHeading: "Documento no encontrado",
    notFoundBody:
      "No pudimos encontrar un documento con ese ID. Puede haberse eliminado, o el enlace puede ser incorrecto.",
    uploadCta: "Subir un documento",
    errorHeading: "Algo salió mal",
    errorBody: "No pudimos cargar este documento en este momento. Inténtalo de nuevo en un momento.",
    tryAgain: "Intentar de nuevo",
    loading: "Cargando documento…",
    precomputedDemoTitle: "Demostración precalculada",
    precomputedDemoBody:
      "Este documento sintético se preparó de antemano. Cargarlo no realiza ninguna llamada a un proveedor de IA.",
    ocrRequiredBody:
      "No se pudo extraer texto útil de este documento. Puede ser una imagen escaneada, y el OCR aún no es compatible, por lo que no puede usarse para preguntas y respuestas.",
  },
  status: {
    parsed: "Procesado",
    ocr_required: "Requiere OCR",
  },
  notFound: {
    heading: "Página no encontrada",
    body: "No pudimos encontrar esa página. Puede que se haya movido, o el enlace puede ser incorrecto.",
    homeCta: "Ir a la página de inicio",
  },
  questions: {
    sectionAriaLabel: "Preguntar a DocuLens",
    preparing: "Preparando este documento para preguntas y respuestas…",
    retryPreparation: "Reintentar preparación",
    emptyHeading: "¿Qué te gustaría saber?",
    emptyBody:
      "Las respuestas están fundamentadas en este documento, con evidencia de página o un resultado honesto de evidencia insuficiente.",
    conversationAriaLabel: "Conversación con DocuLens",
    jumpToLatest: "Ir a lo más reciente ↓",
    composerLabel: "Pregunta lo que quieras sobre este documento",
    composerPlaceholder: "Pregunta lo que quieras sobre este documento…",
    sendAriaLabel: "Enviar pregunta",
    askingLive: "Preguntando a DocuLens. Los turnos anteriores permanecen visibles mientras se prepara una nueva respuesta.",
    enterQuestionError: "Escribe una pregunta antes de consultar a DocuLens.",
    citationPageMismatch: "El servicio de preguntas y respuestas devolvió una cita de una página que no está en este documento.",
    youAskedSr: "Preguntaste: ",
    insufficientEvidenceTitle: "Evidencia insuficiente",
    insufficientEvidenceHint: "Intenta reformular tu pregunta usando términos del documento.",
    thinkingSr: "DocuLens está respondiendo.",
    examplePromptsAriaLabel: "Preguntas de ejemplo",
    examples: [
      "Resume este documento",
      "Identifica los principales riesgos",
      "Enumera los plazos importantes",
      "¿A qué debería prestar atención?",
    ],
    sourcesLabel: "Fuentes",
    citationLabel: "Cita {index}",
    evidenceCitationsAriaLabel: "Citas de la respuesta",
    evidencePageLabel: "Página {page}",
    exampleQuestionSr: "Pregunta de ejemplo: ",
    demoQuestionsAriaLabel: "Preguntas de demostración precalculadas",
    demoBadge: "Demostración precalculada",
    demoHint: "Preparada de antemano: seleccionar una pregunta a continuación nunca llama a un proveedor de IA.",
    demoExampleQuestionsAriaLabel: "Preguntas de demostración de ejemplo",
  },
  errors: {
    networkUnavailable: "No se pudo contactar el servicio de preguntas y respuestas. Inténtalo de nuevo.",
    malformedResponse: "El servicio de preguntas y respuestas devolvió una respuesta inesperada.",
    invalidQuestion: "Escribe una pregunta dentro de la longitud permitida.",
    validQuestionRetry: "Escribe una pregunta válida e inténtalo de nuevo.",
    qaUnavailable: "El servicio de preguntas y respuestas no está disponible en este momento. Inténtalo de nuevo en breve.",
    resetSuffix: " Se restablece a las {time}.",
  },
  metadata: {
    titleTemplate: "%s | DocuLens",
    defaultTitle: "DocuLens — Pregunta a tus documentos, con evidencia",
    description:
      "Sube un PDF y luego hazle preguntas o solicita un análisis. DocuLens fundamenta cada respuesta en la página y la cita exactas de donde proviene, y lo indica cuando el documento no tiene la respuesta.",
    ogAlt: "DocuLens: pregunta a tus documentos, con evidencia",
    manifestDescription: "Sube un PDF y luego hazle preguntas o solicita un análisis fundamentado en evidencia de página exacta.",
  },
  format: {
    pageSingular: "Página {page}",
    pageRange: "Páginas {start}–{end}",
  },
};

export default es;
