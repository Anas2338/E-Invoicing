'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ArrowLeft, BookOpen, FileText, HelpCircle, Mail, Phone } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';

export default function HelpPage() {
  const router = useRouter();

  const faqs = [
    {
      question: 'How do I create an invoice?',
      answer: 'Navigate to the "Create Invoice" page from the dashboard or sidebar. Fill in all required fields including buyer information, seller information, and line items. Click "Save as Draft" to save or "Validate" to check for errors.',
    },
    {
      question: 'What is the difference between SANDBOX and PRODUCTION environments?',
      answer: 'SANDBOX is a testing environment where you can create and validate invoices without submitting them to FBR. PRODUCTION is the live environment where invoices are actually submitted to FBR. You need production access credentials to use the PRODUCTION environment.',
    },
    {
      question: 'How do I validate an invoice?',
      answer: 'Open a draft invoice and click the "Validate" button. The system will check your invoice against FBR validation rules and show any errors that need to be fixed.',
    },
    {
      question: 'How do I post an invoice to FBR?',
      answer: 'After validating an invoice successfully, click the "Post to FBR" button. Make sure you have configured your FBR credentials in Settings and have the necessary permissions.',
    },
    {
      question: 'Where can I find my FBR credentials?',
      answer: 'Go to Settings > FBR Credentials. You can add your FBR access token for both SANDBOX and PRODUCTION environments. Contact your FBR administrator if you need access tokens.',
    },
    {
      question: 'What should I do if my invoice fails validation?',
      answer: 'Review the validation errors shown in the error message. Common issues include missing required fields, invalid tax rates, or incorrect buyer/seller information. Fix the errors and try validating again.',
    },
  ];

  const resources = [
    {
      title: 'FBR E-Invoicing Portal',
      description: 'Official FBR portal for e-invoicing',
      icon: <FileText className="h-6 w-6" />,
      link: 'https://e-invoice.fbr.gov.pk',
    },
    {
      title: 'FBR Documentation',
      description: 'Official documentation and guidelines',
      icon: <BookOpen className="h-6 w-6" />,
      link: 'https://fbr.gov.pk',
    },
  ];

  return (
    <div className="space-y-4 pb-8 max-w-7xl">
      {/* Back to Dashboard Button */}
      <div className="flex items-center gap-4">
        <Button
          variant="outline"
          size="sm"
          onClick={() => router.push('/dashboard')}
          className="flex items-center gap-2"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Dashboard
        </Button>
      </div>

      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Help & Support</h1>
        <p className="mt-2 text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">
          Find answers to common questions and get support for FBR e-invoicing
        </p>
      </div>

      {/* 2-column grid on large screens */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
        {/* Left Column */}
        <div className="space-y-4">
          {/* Contact Support */}
          <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg sm:text-xl">
            <HelpCircle className="h-5 w-5" />
            Contact Support
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-[#dbeafe] dark:bg-[#1e3a8a]/30 rounded-xl flex items-center justify-center">
                  <Mail className="h-6 w-6 text-[#1e40af] dark:text-[#60a5fa]" />
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-1">Email Support</h3>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-2">
                  Get help via email within 24 hours
                </p>
                <a
                  href="https://mail.google.com/mail/?view=cm&to=support@example.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] font-semibold"
                >
                  mohdanus20@gmail.com
                </a>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-[#d1fae5] dark:bg-[#064e3b]/30 rounded-xl flex items-center justify-center">
                  <Phone className="h-6 w-6 text-[#065f46] dark:text-[#34d399]" />
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3] mb-1">Phone Support</h3>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] mb-2">
                  Call us during business hours (9 AM - 5 PM)
                </p>
                <a
                  href="tel:+92-336-2338915"
                  className="text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] font-semibold"
                >
                  +92-336-2338915
                </a>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* FAQs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl">Frequently Asked Questions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {faqs.map((faq, index) => (
              <div key={index} className="border-b border-[#e1e3e5] dark:border-[#2e2e2e] last:border-0 pb-6 last:pb-0">
                <h3 className="text-base font-semibold text-[#202223] dark:text-[#e3e3e3] mb-2">
                  {faq.question}
                </h3>
                <p className="text-sm text-[#6d7175] dark:text-[#8c9196] leading-relaxed">
                  {faq.answer}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

        </div>

        {/* Right Column */}
        <div className="space-y-4">
          {/* Resources */}
          <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl">Helpful Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-3">
            {resources.map((resource, index) => (
              <a
                key={index}
                href={resource.link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-4 p-4 rounded-xl border border-[#e1e3e5] dark:border-[#2e2e2e] hover:border-[#008060] dark:hover:border-[#00a876] hover:bg-[#f1f8f5] dark:hover:bg-[#0d3d2f]/20 transition-all duration-150 group"
              >
                <div className="w-10 h-10 bg-[#f1f8f5] dark:bg-[#0d3d2f]/30 rounded-lg flex items-center justify-center text-[#008060] dark:text-[#00a876] flex-shrink-0">
                  {resource.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-[#202223] dark:text-[#e3e3e3]">{resource.title}</h3>
                  <p className="text-xs text-[#6d7175] dark:text-[#8c9196] truncate">{resource.description}</p>
                </div>
                <svg
                  className="h-4 w-4 text-[#8c9196] dark:text-[#6d7175] flex-shrink-0 group-hover:translate-x-0.5 transition-transform"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick Tips */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl">Quick Tips</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-3">
            <li className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 bg-[#f1f8f5] dark:bg-[#0d3d2f]/30 rounded-full flex items-center justify-center text-[#008060] dark:text-[#00a876] text-xs font-bold mt-0.5">
                1
              </div>
              <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                Always test your invoices in SANDBOX environment before posting to PRODUCTION
              </p>
            </li>
            <li className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 bg-[#f1f8f5] dark:bg-[#0d3d2f]/30 rounded-full flex items-center justify-center text-[#008060] dark:text-[#00a876] text-xs font-bold mt-0.5">
                2
              </div>
              <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                Keep your FBR credentials secure and never share them with unauthorized users
              </p>
            </li>
            <li className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 bg-[#f1f8f5] dark:bg-[#0d3d2f]/30 rounded-full flex items-center justify-center text-[#008060] dark:text-[#00a876] text-xs font-bold mt-0.5">
                3
              </div>
              <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                Validate your invoice before posting to catch errors early
              </p>
            </li>
            <li className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 bg-[#f1f8f5] dark:bg-[#0d3d2f]/30 rounded-full flex items-center justify-center text-[#008060] dark:text-[#00a876] text-xs font-bold mt-0.5">
                4
              </div>
              <p className="text-sm text-[#6d7175] dark:text-[#8c9196]">
                Check the invoice history regularly to monitor the status of your submissions
              </p>
            </li>
          </ul>
        </CardContent>
      </Card>
        </div>
      </div>
    </div>
  );
}
