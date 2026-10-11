import { cva } from 'class-variance-authority';

export const buttonVariants = cva(
  [
    'inline-flex shrink-0 select-none items-center justify-center gap-1.5 whitespace-nowrap',
    'rounded-md font-medium transition-colors duration-150',
    'disabled:pointer-events-none disabled:opacity-50',
    '[&_svg]:pointer-events-none [&_svg]:shrink-0',
  ],
  {
    variants: {
      variant: {
        primary: 'bg-navy-900 text-white shadow-sm hover:bg-navy-800 active:bg-navy-950',
        secondary: 'bg-slate-100 text-navy-900 hover:bg-slate-200 active:bg-slate-300',
        outline:
          'border border-slate-300 bg-white text-slate-800 shadow-sm hover:border-slate-400 hover:bg-slate-50',
        ghost: 'text-slate-700 hover:bg-slate-100 hover:text-navy-900',
        danger: 'bg-red-600 text-white shadow-sm hover:bg-red-700 active:bg-red-800',
        link: 'h-auto px-0 text-teal-700 underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-8 px-2.5 text-xs [&_svg]:size-3.5',
        md: 'h-9 px-3.5 text-sm [&_svg]:size-4',
        icon: 'size-8 p-0 [&_svg]:size-4',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
);
