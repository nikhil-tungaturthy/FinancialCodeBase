import type { Tone } from '@/types/domain';

/** Soft-filled badge styling per semantic tone (text contrast ≥ 4.5:1 on each fill). */
export const TONE_BADGE_CLASSES: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
  info: 'bg-sky-50 text-sky-800 ring-sky-200',
  success: 'bg-green-100 text-green-600 ring-green-200',
  warning: 'bg-amber-100 text-amber-600 ring-amber-200',
  danger: 'bg-red-100 text-red-700 ring-red-200',
  navy: 'bg-navy-900/5 text-navy-800 ring-navy-900/10',
  teal: 'bg-teal-100 text-teal-700 ring-teal-200',
};

export const TONE_DOT_CLASSES: Record<Tone, string> = {
  neutral: 'bg-slate-400',
  info: 'bg-sky-500',
  success: 'bg-green-600',
  warning: 'bg-amber-500',
  danger: 'bg-red-600',
  navy: 'bg-navy-700',
  teal: 'bg-teal-600',
};

export const TONE_TEXT_CLASSES: Record<Tone, string> = {
  neutral: 'text-slate-600',
  info: 'text-sky-700',
  success: 'text-green-600',
  warning: 'text-amber-600',
  danger: 'text-red-600',
  navy: 'text-navy-800',
  teal: 'text-teal-700',
};

export const TONE_ICON_BG_CLASSES: Record<Tone, string> = {
  neutral: 'bg-slate-100 text-slate-600',
  info: 'bg-sky-50 text-sky-700',
  success: 'bg-green-100 text-green-600',
  warning: 'bg-amber-100 text-amber-600',
  danger: 'bg-red-100 text-red-600',
  navy: 'bg-navy-900 text-white',
  teal: 'bg-teal-100 text-teal-700',
};
