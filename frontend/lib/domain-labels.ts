/** UI-only Persian labels for known API enum values.
 * Do not change the wire values, translate user content, or guess unknown states.
 * Unknown values remain visible for safe operational diagnosis.
 */
function displayLabel(labels: Readonly<Record<string, string>>, value: string | null | undefined): string {
  if (!value) return "—";
  return labels[value] ?? value;
}

const riskLevels: Readonly<Record<string, string>> = {
  low: "پایین",
  medium: "متوسط",
  high: "بالا",
  critical: "بحرانی",
};

const riskStatuses: Readonly<Record<string, string>> = {
  open: "باز",
  draft: "پیش‌نویس",
  in_review: "در بازبینی",
  under_review: "در بازبینی",
  in_treatment: "در حال درمان",
  treatment_in_progress: "در حال درمان",
  accepted: "پذیرفته‌شده",
  mitigated: "کاهش‌یافته",
  closed: "بسته",
};

const controlStatuses: Readonly<Record<string, string>> = {
  draft: "پیش‌نویس",
  active: "فعال",
  inactive: "غیرفعال",
  archived: "بایگانی‌شده",
  deprecated: "منسوخ",
};

const controlTypes: Readonly<Record<string, string>> = {
  technical: "فنی",
  administrative: "اداری",
  organizational: "سازمانی",
  managerial: "مدیریتی",
  physical: "فیزیکی",
  procedural: "رویه‌ای",
  other: "سایر",
};

const controlNatures: Readonly<Record<string, string>> = {
  preventive: "پیشگیرانه",
  detective: "کشف‌کننده",
  corrective: "اصلاحی",
  deterrent: "بازدارنده",
  compensating: "جبرانی",
  recovery: "بازیابی",
  other: "سایر",
};

const classifications: Readonly<Record<string, string>> = {
  public: "عمومی",
  internal: "داخلی",
  confidential: "محرمانه",
  secret: "خیلی محرمانه",
};

const evidenceTypes: Readonly<Record<string, string>> = {
  file: "فایل",
  url: "نشانی اینترنتی",
  text: "متن",
  screenshot: "تصویر صفحه",
  report: "گزارش",
  log: "گزارش رخداد",
  configuration: "پیکربندی",
  other: "سایر",
};

export const riskLevelLabel = (value?: string | null) => displayLabel(riskLevels, value);
export const riskStatusLabel = (value?: string | null) => displayLabel(riskStatuses, value);
export const controlStatusLabel = (value?: string | null) => displayLabel(controlStatuses, value);
export const controlTypeLabel = (value?: string | null) => displayLabel(controlTypes, value);
export const controlNatureLabel = (value?: string | null) => displayLabel(controlNatures, value);
export const evidenceClassificationLabel = (value?: string | null) => displayLabel(classifications, value);
export const evidenceTypeLabel = (value?: string | null) => displayLabel(evidenceTypes, value);
