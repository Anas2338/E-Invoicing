export default function Loading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      <div className="text-center">
        {/* Spinner Container */}
        <div className="relative inline-flex">
          {/* Outer Ring */}
          <div className="w-24 h-24 rounded-full border-4 border-indigo-100"></div>

          {/* Spinning Ring */}
          <div className="absolute top-0 left-0 w-24 h-24 rounded-full border-4 border-transparent border-t-indigo-600 border-r-indigo-600 animate-spin"></div>

          {/* Inner Circle */}
          <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-16 h-16 rounded-full bg-indigo-50 flex items-center justify-center">
            <div className="w-8 h-8 rounded-full bg-indigo-600 animate-pulse"></div>
          </div>
        </div>

        {/* Loading Text */}
        <div className="mt-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Loading</h2>
          <p className="text-gray-600 animate-pulse">Please wait while we load your content...</p>
        </div>

        {/* Loading Dots Animation */}
        <div className="flex justify-center items-center space-x-2 mt-6">
          <div className="w-3 h-3 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
          <div className="w-3 h-3 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
          <div className="w-3 h-3 bg-indigo-600 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
        </div>
      </div>
    </div>
  );
}
