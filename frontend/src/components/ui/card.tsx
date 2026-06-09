import * as React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}
interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}
interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}
interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}
interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={`border-2 border-blue-300 rounded-2xl bg-white text-[#202223] shadow-sm transition-shadow duration-150 hover:shadow-md ${className}`}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: CardHeaderProps) {
  return (
    <div className={`flex flex-col space-y-1.5 p-1 ${className}`} {...props} />
  );
}

export function CardTitle({ className, ...props }: CardTitleProps) {
  return (
    <div
      className={`text-sm font-extrabold leading-tight tracking-tight ${className}`}
      {...props}
    />
  );
}

export function CardDescription({ className, ...props }: CardDescriptionProps) {
  return (
    <p
      className={`text-sm text-[#6d7175] dark:text-[#8c9196] ${className}`}
      {...props}
    />
  );
}

export function CardContent({ className, ...props }: CardContentProps) {
  return <div className={`p-1 ${className}`} {...props} />;
}
