'use client';

import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import SavedItemsSection from '@/components/profile/SavedItemsSection';
import { ArrowLeft } from 'lucide-react';

export default function ProductsPage() {
  const router = useRouter();

  return (
    <div className="space-y-4 max-w-7xl">
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

      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-[#202223] dark:text-[#e3e3e3]">Items</h1>
        <p className="mt-2 text-sm sm:text-base text-[#6d7175] dark:text-[#8c9196]">Manage your saved items, products, and services</p>
      </div>

      <SavedItemsSection />
    </div>
  );
}
