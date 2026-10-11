import {
  AlertTriangle,
  ArrowLeftRight,
  History,
  Landmark,
  LayoutDashboard,
  ShieldCheck,
  SlidersHorizontal,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  /** Matches nested routes (e.g. `/payments/MGB-PAY-1042`). */
  end?: boolean;
  testId: string;
}

/** Primary navigation — one entry per top-level route in SPEC §8. */
export const NAV_ITEMS: readonly NavItem[] = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true, testId: 'nav-overview' },
  { to: '/payments', label: 'Payments', icon: ArrowLeftRight, testId: 'nav-payments' },
  { to: '/exceptions', label: 'Exceptions', icon: AlertTriangle, testId: 'nav-exceptions' },
  { to: '/settlement', label: 'Settlement', icon: Landmark, testId: 'nav-settlement' },
  { to: '/approvals', label: 'Approvals', icon: ShieldCheck, testId: 'nav-approvals' },
  { to: '/audit', label: 'Audit', icon: History, testId: 'nav-audit' },
  { to: '/policies', label: 'Policies', icon: SlidersHorizontal, testId: 'nav-policies' },
];

export interface RouteHandle {
  /** Page title shown in the top bar and document title. */
  title: string | ((params: Record<string, string | undefined>) => string);
}

export const APP_NAME = 'Meridian Flow';
export const APP_TAGLINE = 'Global Payments & Exception Operations';
export const ENVIRONMENT_TAG = 'DEMO · SYNTHETIC DATA';
