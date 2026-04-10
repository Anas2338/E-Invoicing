import { Zap, CheckCircle, Shield, BarChart3 } from 'lucide-react';

const features = [
  {
    icon: Zap,
    title: 'Automated Invoice Processing',
    description: 'Upload Excel files and process multiple invoices automatically. Save time with intelligent data extraction and batch operations.',
  },
  {
    icon: CheckCircle,
    title: 'Real-time Validation',
    description: 'Instant validation against FBR regulations. Ensure compliance before submission with comprehensive error checking.',
  },
  {
    icon: Shield,
    title: 'Secure Data Management',
    description: 'Enterprise-grade encryption protects your sensitive invoice data. Built with security and privacy as top priorities.',
  },
  {
    icon: BarChart3,
    title: 'Comprehensive Reporting',
    description: 'Track all invoice activities with detailed history and status reports. Monitor validation results and submission records.',
  },
];

export default function FeatureHighlights() {
  return (
    <div className="space-y-6">
      <div className="text-center lg:text-left">
        <h1 className="text-4xl font-bold text-[#202223] dark:text-[#e3e3e3] tracking-tight">
          E-Invoicing Platform
        </h1>
        <p className="mt-3 text-lg text-[#6d7175] dark:text-[#8c9196]">
          Streamline your invoice management with automated processing and compliance
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
        {features.map((feature) => {
          const Icon = feature.icon;
          return (
            <div
              key={feature.title}
              className="bg-white dark:bg-[#1a1a1a] p-5 rounded-xl shadow-md border border-[#e1e3e5] dark:border-[#2e2e2e] transition-all duration-150 hover:shadow-lg"
            >
              <div className="flex items-start space-x-4">
                <div className="flex-shrink-0">
                  <div className="flex items-center justify-center h-12 w-12 rounded-lg bg-[#f1f8f5] dark:bg-[#0d3d2f]/30">
                    <Icon className="h-6 w-6 text-[#008060] dark:text-[#00a876]" />
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3] mb-1">
                    {feature.title}
                  </h3>
                  <p className="text-sm text-[#6d7175] dark:text-[#8c9196] leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
