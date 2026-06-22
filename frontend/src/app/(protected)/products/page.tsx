'use client';

import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import SavedItemsSection, { SavedItemsSectionHandle } from '@/components/profile/SavedItemsSection';
import { ArrowLeft, Download, Upload, Plus, Loader2 } from 'lucide-react';

export default function ProductsPage() {
  const router = useRouter();
  const savedItemsRef = useRef<SavedItemsSectionHandle>(null);
  const [downloadingTemplate, setDownloadingTemplate] = useState(false);

  const handleDownload = async () => {
    setDownloadingTemplate(true);
    try {
      await savedItemsRef.current?.downloadTemplate();
    } finally {
      setDownloadingTemplate(false);
    }
  };

  return (
    <div className="h-full flex flex-col space-y-2 sm:space-y-3">
      {/* Content + Actions Sidebar */}
      <div className="flex flex-col md:flex-row gap-0 flex-1 min-h-0">
        {/* Action Bar — horizontal on mobile, vertical on tablet+ */}
        <div className="flex flex-row md:flex-col items-center justify-center md:justify-start gap-1 sm:gap-1.5 py-2 md:py-0 md:pt-32 px-1 md:px-1 md:pr-1.5 flex-shrink-0 overflow-x-auto">
          <Button
            variant="outline"
            size="icon"
            onClick={() => router.push('/dashboard')}
            className="h-8 w-8 border-orange-200"
            title="Back to Dashboard"
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={handleDownload}
            disabled={downloadingTemplate}
            className="h-8 w-8 border-blue-300 text-[#1e40af]"
            title="Download Template"
          >
            {downloadingTemplate ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={() => savedItemsRef.current?.triggerFileUpload()}
            className="h-8 w-8 border-green-300"
            title="Upload Excel"
          >
            <Upload className="h-4 w-4" />
          </Button>
          <Button
            size="icon"
            onClick={() => savedItemsRef.current?.openAddForm()}
            className="h-8 w-8 !bg-white !text-[#008060] !border-2 !border-green-300"
            title="Add Item"
          >
            <Plus className="h-4 w-4" />
          </Button>
        </div>

        {/* Main Content */}
        <div className="flex-1 min-h-0 flex flex-col">
          <SavedItemsSection ref={savedItemsRef} hideHeaderActions />
        </div>
      </div>
    </div>
  );
}
