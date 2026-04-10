'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import AutomationDashboard from '@/components/automation/AutomationDashboard';
import InvoiceList from '@/components/automation/InvoiceList';
import InvoiceDetail from '@/components/automation/InvoiceDetail';
import { AutomationInvoice } from '@/services/automationApi';
import { ArrowLeft } from 'lucide-react';

export default function DashboardPage() {
  const router = useRouter();
  const [selectedInvoice, setSelectedInvoice] = useState<AutomationInvoice | null>(null);

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl">
      <div className="flex items-center gap-4 mb-6">
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

      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[#202223] dark:text-[#e3e3e3] mb-2">
          Automation Dashboard
        </h1>
        <p className="text-[#6d7175] dark:text-[#8c9196]">
          Monitor invoice processing status and view detailed statistics
        </p>
      </div>

      {selectedInvoice ? (
        <div className="mb-8">
          <button
            onClick={() => setSelectedInvoice(null)}
            className="mb-4 text-sm text-[#008060] dark:text-[#00a876] hover:text-[#006e52] dark:hover:text-[#008f64] font-semibold flex items-center gap-1"
          >
            ← Back to list
          </button>
          <InvoiceDetail
            invoiceId={selectedInvoice.id}
            onClose={() => setSelectedInvoice(null)}
          />
        </div>
      ) : (
        <div className="space-y-8">
          <AutomationDashboard />
          <InvoiceList onInvoiceClick={setSelectedInvoice} />
        </div>
      )}
    </div>
  );
}
