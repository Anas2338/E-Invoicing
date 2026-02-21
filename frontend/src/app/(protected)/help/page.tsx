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
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-4 mb-2">
            <Button variant="ghost" onClick={() => router.push('/dashboard')}>
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Dashboard
            </Button>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Help & Support</h1>
          <p className="mt-2 text-sm sm:text-base text-gray-600">
            Find answers to common questions and get support for FBR e-invoicing
          </p>
        </div>
      </div>

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
                <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center">
                  <Mail className="h-6 w-6 text-indigo-600" />
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-1">Email Support</h3>
                <p className="text-sm text-gray-600 mb-2">
                  Get help via email within 24 hours
                </p>
                <a
                  href="https://mail.google.com/mail/?view=cm&to=support@example.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-indigo-600 hover:text-indigo-500 font-medium"
                >
                  mohdanus20@gmail.com
                </a>
              </div>
            </div>

            <div className="flex items-start gap-4">
              <div className="flex-shrink-0">
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center">
                  <Phone className="h-6 w-6 text-green-600" />
                </div>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900 mb-1">Phone Support</h3>
                <p className="text-sm text-gray-600 mb-2">
                  Call us during business hours (9 AM - 5 PM)
                </p>
                <a
                  href="tel:+92-51-1234567"
                  className="text-sm text-green-600 hover:text-green-500 font-medium"
                >
                  +92-51-1234567
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
              <div key={index} className="border-b border-gray-200 last:border-0 pb-6 last:pb-0">
                <h3 className="text-base font-semibold text-gray-900 mb-2">
                  {faq.question}
                </h3>
                <p className="text-sm text-gray-600 leading-relaxed">
                  {faq.answer}
                </p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Resources */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg sm:text-xl">Helpful Resources</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {resources.map((resource, index) => (
              <a
                key={index}
                href={resource.link}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-start gap-4 p-4 rounded-lg border-2 border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 transition-colors"
              >
                <div className="flex-shrink-0">
                  <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center text-indigo-600">
                    {resource.icon}
                  </div>
                </div>
                <div className="flex-1">
                  <h3 className="text-sm font-semibold text-gray-900 mb-1">
                    {resource.title}
                  </h3>
                  <p className="text-xs text-gray-600">
                    {resource.description}
                  </p>
                </div>
                <svg
                  className="h-5 w-5 text-gray-400 flex-shrink-0"
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
              <div className="flex-shrink-0 w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 text-xs font-bold mt-0.5">
                1
              </div>
              <p className="text-sm text-gray-600">
                Always test your invoices in SANDBOX environment before posting to PRODUCTION
              </p>
            </li>
            <li className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 text-xs font-bold mt-0.5">
                2
              </div>
              <p className="text-sm text-gray-600">
                Keep your FBR credentials secure and never share them with unauthorized users
              </p>
            </li>
            <li className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 text-xs font-bold mt-0.5">
                3
              </div>
              <p className="text-sm text-gray-600">
                Validate your invoice before posting to catch errors early
              </p>
            </li>
            <li className="flex items-start gap-3">
              <div className="flex-shrink-0 w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 text-xs font-bold mt-0.5">
                4
              </div>
              <p className="text-sm text-gray-600">
                Check the invoice history regularly to monitor the status of your submissions
              </p>
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
